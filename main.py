from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pulp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    # 1. 가격 정의
    prices = {
        "영생의 아쿠티스": 5159, "크라켄의 광란체": 5234, "리바이던의 깃털": 5393,
        "해구의 파동 코어": 11131, "침묵의 심해 비약": 11242, "청해룡의 날개": 11399,
        "아쿠아 펄스 파편": 21833, "나우틸러스의 손": 22088, "무저의 척추": 22227,
        "추출된 희석액": 18444
    }
    
    tier_map = {
        "추출된 희석액": "0", "영생의 아쿠티스": "1", "크라켄의 광란체": "1", "리바이던의 깃털": "1",
        "해구의 파동 코어": "2", "침묵의 심해 비약": "2", "청해룡의 날개": "2",
        "아쿠아 펄스 파편": "3", "나우틸러스의 손": "3", "무저의 척추": "3"
    }

    finished_goods = list(prices.keys())
    
    # 2. 완성품 레시피
    recipes = {
        "영생의 아쿠티스": {"물결 수호의 핵": 1, "질서 파괴의 핵": 1, "활력 붕괴의 핵": 1},
        "크라켄의 광란체": {"질서 파괴의 핵": 1, "활력 붕괴의 핵": 1, "파동 오염의 핵": 1},
        "리바이던의 깃털": {"침식 방어의 핵": 1, "파동 오염의 핵": 1, "물결 수호의 핵": 1},
        "해구의 파동 코어": {"활기 보존의 결정": 1, "파도 침식의 결정": 1, "격류 재생의 결정": 1},
        "침묵의 심해 비약": {"파도 침식의 결정": 1, "격류 재생의 결정": 1, "맹독 혼란의 결정": 1},
        "청해룡의 날개": {"방어 오염의 결정": 1, "맹독 혼란의 결정": 1, "활기 보존의 결정": 1},
        "아쿠아 펄스 파편": {"불멸 재생의 영약": 1, "파동 장벽의 영약": 1, "맹독 파동의 영약": 1},
        "나우틸러스의 손": {"파동 장벽의 영약": 1, "생명 광란의 영약": 1, "불멸 재생의 영약": 1},
        "무저의 척추": {"타락 침식의 영약": 1, "맹독 파동의 영약": 1, "생명 광란의 영약": 1},
        "추출된 희석액": {"침식 방어의 핵": 3, "방어 오염의 결정": 2, "타락 침식의 영약": 1}
    }

    # 3. 중간재료(조합품) 레시피 -> 가공품 요구량
    inter_recipes = {
        "물결 수호의 핵": {"수호의 정수": 1, "파동의 정수": 1}, "파동 오염의 핵": {"파동의 정수": 1, "혼란의 정수": 1},
        "질서 파괴의 핵": {"혼란의 정수": 1, "생명의 정수": 1}, "활력 붕괴의 핵": {"생명의 정수": 1, "부식의 정수": 1}, "침식 방어의 핵": {"부식의 정수": 1, "수호의 정수": 1},
        "활기 보존의 결정": {"수호 에센스": 1, "생명 에센스": 1}, "파도 침식의 결정": {"파동 에센스": 1, "부식 에센스": 1},
        "방어 오염의 결정": {"혼란 에센스": 1, "수호 에센스": 1}, "격류 재생의 결정": {"생명 에센스": 1, "파동 에센스": 1}, "맹독 혼란의 결정": {"부식 에센스": 1, "혼란 에센스": 1},
        "불멸 재생의 영약": {"수호의 엘릭서": 1, "생명의 엘릭서": 1}, "파동 장벽의 영약": {"파동의 엘릭서": 1, "수호의 엘릭서": 1},
        "타락 침식의 영약": {"혼란의 엘릭서": 1, "부식의 엘릭서": 1}, "생명 광란의 영약": {"생명의 엘릭서": 1, "혼란의 엘릭서": 1}, "맹독 파동의 영약": {"부식의 엘릭서": 1, "파동의 엘릭서": 1}
    }

    # 4. 가공품 -> 어패류 1:1 매핑
    raw_mapping = {
        "수호의 정수": "1_굴", "파동의 정수": "1_소라", "혼란의 정수": "1_문어", "생명의 정수": "1_미역", "부식의 정수": "1_성게",
        "수호 에센스": "2_굴", "파동 에센스": "2_소라", "혼란 에센스": "2_문어", "생명 에센스": "2_미역", "부식 에센스": "2_성게",
        "수호의 엘릭서": "3_굴", "파동의 엘릭서": "3_소라", "혼란의 엘릭서": "3_문어", "생명의 엘릭서": "3_미역", "부식의 엘릭서": "3_성게"
    }

    # 5. 부가 재료 요구량 (단위 생산당 소모량으로 정규화)
    extra_reqs = {
        "수호의 정수": {"점토": 1}, "파동의 정수": {"모래": 2}, "혼란의 정수": {"흙": 4}, "생명의 정수": {"자갈": 2}, "부식의 정수": {"화강암": 1},
        "물결 수호의 핵": {"깐 새우": 1}, "파동 오염의 핵": {"도미 회": 1}, "질서 파괴의 핵": {"청어 회": 1}, "활력 붕괴의 핵": {"금붕어 회": 1}, "침식 방어의 핵": {"농어 회": 1},
        "수호 에센스": {"해초": 3, "참나무 잎": 3}, "파동 에센스": {"해초": 3, "가문비나무 잎": 3}, "혼란 에센스": {"해초": 3, "자작나무 잎": 3}, "생명 에센스": {"해초": 3, "벚나무 잎": 3}, "부식 에센스": {"해초": 3, "짙은 참나무 잎": 3},
        "활기 보존의 결정": {"켈프": 8, "청금석 블록": 1}, "파도 침식의 결정": {"켈프": 8, "레드스톤 블록": 1}, "방어 오염의 결정": {"켈프": 8, "철 주괴": 3}, "격류 재생의 결정": {"켈프": 8, "금 주괴": 2}, "맹독 혼란의 결정": {"켈프": 8, "다이아몬드": 1},
        "수호의 엘릭서": {"불우렁쉥이": 2, "유리병": 3, "네더랙": 8}, "파동의 엘릭서": {"불우렁쉥이": 2, "유리병": 3, "마그마 블록": 4}, "혼란의 엘릭서": {"불우렁쉥이": 2, "유리병": 3, "영혼 흙": 4}, "생명의 엘릭서": {"불우렁쉥이": 2, "유리병": 3, "진홍빛 자루": 4}, "부식의 엘릭서": {"불우렁쉥이": 2, "유리병": 3, "뒤틀린 자루": 4},
        "불멸 재생의 영약": {"말린 켈프": 12, "발광 열매": 4, "죽은 관 산호 블록": 2}, "파동 장벽의 영약": {"말린 켈프": 12, "발광 열매": 4, "죽은 사방산호 블록": 2}, "타락 침식의 영약": {"말린 켈프": 12, "발광 열매": 4, "죽은 거품 산호 블록": 2}, "생명 광란의 영약": {"말린 켈프": 12, "발광 열매": 4, "죽은 불 산호 블록": 2}, "맹독 파동의 영약": {"말린 켈프": 12, "발광 열매": 4, "죽은 뇌 산호 블록": 2}
    }
    
    block_types = {"점토", "모래", "흙", "자갈", "화강암", "청금석 블록", "레드스톤 블록", "마그마 블록", "영혼 흙", "네더랙", "죽은 관 산호 블록", "죽은 사방산호 블록", "죽은 거품 산호 블록", "죽은 불 산호 블록", "죽은 뇌 산호 블록"}

    inter_names = list(inter_recipes.keys())
    refined_names = list(raw_mapping.keys())

    def solve(mode="profit"):
        model = pulp.LpProblem("Alchemy_Crafting", pulp.LpMaximize)

        f_vars = {f: pulp.LpVariable(f"f_{f}", lowBound=0, cat='Integer') for f in finished_goods}
        c_vars = {i: pulp.LpVariable(f"c_{i}", lowBound=0, cat='Integer') for i in inter_names}
        hc_vars = {i: pulp.LpVariable(f"hc_{i}", lowBound=0, cat='Integer') for i in inter_names if "핵" in i or "결정" in i}
        r_made_vars = {r: pulp.LpVariable(f"rm_{r}", lowBound=0, cat='Integer') for r in refined_names}

        # 1성(핵), 2성(결정) 제작량 짝수 
        for i in hc_vars:
            model += c_vars[i] == 2 * hc_vars[i]

        # 조합품 잔여 0 규칙
        for i in inter_names:
            demand = pulp.lpSum(recipes[f].get(i, 0) * f_vars[f] for f in finished_goods)
            model += demand == c_vars[i] + data.inter.get(i, 0)

        # 가공품 요구량 및 원재료 소모 제약
        for r in refined_names:
            ref_demand = pulp.lpSum(inter_recipes[i].get(r, 0) * c_vars[i] for i in inter_names)
            model += ref_demand == r_made_vars[r] + data.refined.get(r, 0)
            model += r_made_vars[r] <= data.raw.get(raw_mapping[r], 0)

        profit = pulp.lpSum(prices[f] * f_vars[f] for f in finished_goods)
        if mode == "profit":
            model += profit
        else:
            total_raw_used = pulp.lpSum(r_made_vars[r] for r in refined_names)
            model += total_raw_used * 1000000 + profit

        model.solve(pulp.PULP_CBC_CMD(msg=False))

        if pulp.LpStatus[model.status] == 'Optimal':
            result_f = {k: int(v.varValue) for k, v in f_vars.items() if int(v.varValue) > 0}
            result_c = {k: int(v.varValue) for k, v in c_vars.items() if int(v.varValue) > 0}
            result_r_made = {k: int(v.varValue) for k, v in r_made_vars.items() if int(v.varValue) > 0}
            
            # 매출 요약 계산
            sales_by_tier = {"0": 0, "1": 0, "2": 0, "3": 0}
            total_profit = 0
            for k, v in result_f.items():
                p = prices[k] * v
                total_profit += p
                sales_by_tier[tier_map[k]] += p

            # 추가 재료 계산
            materials_raw = {}
            materials_block = {}
            materials_other = {}

            # 사용된 어패류 계산
            for r_name in refined_names:
                made = int(r_made_vars[r_name].varValue)
                if made > 0:
                    raw_id = raw_mapping[r_name]
                    materials_raw[raw_id] = materials_raw.get(raw_id, 0) + made

            # 부가 재료 합산 함수
            def add_extras(item_dict):
                for item_name, count in item_dict.items():
                    if item_name in extra_reqs:
                        for mat, qty in extra_reqs[item_name].items():
                            total_needed = qty * count
                            if mat in block_types:
                                materials_block[mat] = materials_block.get(mat, 0) + total_needed
                            else:
                                materials_other[mat] = materials_other.get(mat, 0) + total_needed

            add_extras(result_c)
            add_extras(result_r_made)

            # 티어별로 가공품/조합품 정리하여 응답
            craft_1 = {**{k:v for k,v in result_r_made.items() if "정수" in k}, **{k:v for k,v in result_c.items() if "핵" in k}}
            craft_2 = {**{k:v for k,v in result_r_made.items() if "에센스" in k}, **{k:v for k,v in result_c.items() if "결정" in k}}
            craft_3 = {**{k:v for k,v in result_r_made.items() if "엘릭서" in k}, **{k:v for k,v in result_c.items() if "영약" in k}}

            return {
                "success": True,
                "profit": total_profit,
                "sales_by_tier": sales_by_tier,
                "final_goods": result_f,
                "craft_1": craft_1,
                "craft_2": craft_2,
                "craft_3": craft_3,
                "materials_raw": materials_raw,
                "materials_block": materials_block,
                "materials_other": materials_other
            }
        return {"success": False}

    return {
        "route1": solve("profit"),
        "route2": solve("zero_waste")
    }