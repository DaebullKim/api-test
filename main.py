# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pulp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 실제 운영시 Cloudflare 도메인으로 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InventoryData(BaseModel):
    raw: dict
    refined: dict
    inter: dict

@app.post("/api/calculate")
def calculate_optimal_route(data: InventoryData):
    # 가격 및 레시피 정의
    prices = {"아쿠티스": 5159, "광란체": 5234, "깃털": 5393, "코어": 11131, "비약": 11242, "날개": 11399, "파편": 21833, "손": 22088, "척추": 22227, "희석액": 18444}
    finished_goods = list(prices.keys())
    
    recipes = {
        "아쿠티스": {"1_물결 수호": 1, "1_질서 파괴": 1, "1_활력 붕괴": 1},
        "광란체": {"1_질서 파괴": 1, "1_활력 붕괴": 1, "1_파동 오염": 1},
        "깃털": {"1_침식 방어": 1, "1_파동 오염": 1, "1_물결 수호": 1},
        "코어": {"2_활기 보존": 1, "2_파도 침식": 1, "2_격류 재생": 1},
        "비약": {"2_파도 침식": 1, "2_격류 재생": 1, "2_맹독 혼란": 1},
        "날개": {"2_방어 오염": 1, "2_맹독 혼란": 1, "2_활기 보존": 1},
        "파편": {"3_불멸 재생": 1, "3_파동 장벽": 1, "3_맹독 파동": 1},
        "손": {"3_불멸 재생": 1, "3_파동 장벽": 1, "3_생명 광란": 1},
        "척추": {"3_맹독 파동": 1, "3_생명 광란": 1, "3_타락 침식": 1},
        "희석액": {"1_침식 방어": 3, "2_방어 오염": 2, "3_타락 침식": 1}
    }

    # 중간재료 레시피 (정수/에센스/엘릭서 요구량)
    inter_recipes = {
        # 1성
        "1_물결 수호": {"1_수호정": 1, "1_파동정": 1}, "1_파동 오염": {"1_파동정": 1, "1_혼란정": 1},
        "1_질서 파괴": {"1_혼란정": 1, "1_생명정": 1}, "1_활력 붕괴": {"1_생명정": 1, "1_부식정": 1}, "1_침식 방어": {"1_부식정": 1, "1_수호정": 1},
        # 2성
        "2_활기 보존": {"2_수호 에센스": 1, "2_생명 에센스": 1}, "2_파도 침식": {"2_파동 에센스": 1, "2_부식 에센스": 1},
        "2_방어 오염": {"2_혼란 에센스": 1, "2_수호 에센스": 1}, "2_격류 재생": {"2_생명 에센스": 1, "2_파동 에센스": 1}, "2_맹독 혼란": {"2_부식 에센스": 1, "2_혼란 에센스": 1},
        # 3성
        "3_불멸 재생": {"3_수호 엘릭서": 1, "3_생명 엘릭서": 1}, "3_파동 장벽": {"3_파동 엘릭서": 1, "3_수호 엘릭서": 1},
        "3_타락 침식": {"3_혼란 엘릭서": 1, "3_부식 엘릭서": 1}, "3_생명 광란": {"3_생명 엘릭서": 1, "3_혼란 엘릭서": 1}, "3_맹독 파동": {"3_부식 엘릭서": 1, "3_파동 엘릭서": 1}
    }

    # 정수 -> 원재료 매핑
    raw_mapping = {
        "1_수호정": "1_굴", "1_파동정": "1_소라", "1_혼란정": "1_문어", "1_생명정": "1_미역", "1_부식정": "1_성게",
        "2_수호 에센스": "2_굴", "2_파동 에센스": "2_소라", "2_혼란 에센스": "2_문어", "2_생명 에센스": "2_미역", "2_부식 에센스": "2_성게",
        "3_수호 엘릭서": "3_굴", "3_파동 엘릭서": "3_소라", "3_혼란 엘릭서": "3_문어", "3_생명 엘릭서": "3_미역", "3_부식 엘릭서": "3_성게"
    }

    inter_names = list(inter_recipes.keys())
    refined_names = list(raw_mapping.keys())
    raw_names = list(raw_mapping.values())

    def solve(mode="profit"):
        model = pulp.LpProblem("Crafting", pulp.LpMaximize)

        f_vars = {f: pulp.LpVariable(f"f_{f}", lowBound=0, cat='Integer') for f in finished_goods}
        c_vars = {i: pulp.LpVariable(f"c_{i}", lowBound=0, cat='Integer') for i in inter_names}
        hc_vars = {i: pulp.LpVariable(f"hc_{i}", lowBound=0, cat='Integer') for i in inter_names if i.startswith("1_") or i.startswith("2_")}
        r_made_vars = {r: pulp.LpVariable(f"rm_{r}", lowBound=0, cat='Integer') for r in refined_names}

        # 1. 1성, 2성 중간재료 제작량 짝수 규칙
        for i in hc_vars:
            model += c_vars[i] == 2 * hc_vars[i]

        # 2. 중간재료 잔여 0 규칙 (요구량 = 제작량 + 기존재고)
        for i in inter_names:
            demand = pulp.lpSum(recipes[f].get(i, 0) * f_vars[f] for f in finished_goods)
            model += demand == c_vars[i] + data.inter.get(i, 0)

        # 3. 가공품(정수 등) 요구량 및 원재료 소모 제약
        for r in refined_names:
            # 해당 가공품을 요구하는 중간재료의 제작수량 총합
            ref_demand = pulp.lpSum(inter_recipes[i].get(r, 0) * c_vars[i] for i in inter_names)
            # 가공품 요구량 = 원재료에서 변환한 양 + 가공품 기존재고
            model += ref_demand == r_made_vars[r] + data.refined.get(r, 0)
            # 원재료에서 변환한 양은 원재료 재고를 초과할 수 없음
            model += r_made_vars[r] <= data.raw.get(raw_mapping[r], 0)

        # 4. 목적 함수 설정
        profit = pulp.lpSum(prices[f] * f_vars[f] for f in finished_goods)
        if mode == "profit":
            model += profit
        else:
            # 재료 소진 최우선 (남은 원재료 최소화 = 사용 원재료 최대화)
            total_raw_used = pulp.lpSum(r_made_vars[r] for r in refined_names)
            model += total_raw_used * 1000000 + profit

        model.solve(pulp.PULP_CBC_CMD(msg=False))

        if pulp.LpStatus[model.status] == 'Optimal':
            result_f = {k: int(v.varValue) for k, v in f_vars.items() if int(v.varValue) > 0}
            result_c = {k: int(v.varValue) for k, v in c_vars.items() if int(v.varValue) > 0}
            result_r_made = {k: int(v.varValue) for k, v in r_made_vars.items() if int(v.varValue) > 0}
            
            # 남은 원재료 계산
            raw_remains = {}
            for r in refined_names:
                r_name = raw_mapping[r]
                left = data.raw.get(r_name, 0) - int(r_made_vars[r].varValue)
                if left > 0:
                    raw_remains[r_name] = left

            total_profit = sum(prices[k] * v for k, v in result_f.items())

            return {
                "success": True,
                "profit": total_profit,
                "final_goods": result_f,
                "inter_craft": result_c,
                "refined_craft": result_r_made,
                "raw_remains": raw_remains
            }
        return {"success": False}

    return {
        "route1": solve("profit"),
        "route2": solve("zero_waste")
    }