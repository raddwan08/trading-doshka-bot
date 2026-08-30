from analysis.wyckoff import wyckoff_analysis
from analysis.elliott import elliott_analysis
from analysis.harmonic import harmonic_analysis
from analysis.classic import classic_analysis
from analysis.whales import whales_analysis


ANALYZERS = {

    "wyckoff": wyckoff_analysis,
    "elliott": elliott_analysis,
    "harmonic": harmonic_analysis,
    "classic": classic_analysis,
    "whales": whales_analysis

}



async def run_analysis(
    school,
    data,
    symbol
):

    if data.empty:

        return {
            "text":"لا توجد بيانات",
            "entry":[],
            "levels":[]
        }


    analyzer = ANALYZERS.get(school)


    if not analyzer:

        return {
            "text":"مدرسة غير موجودة",
            "entry":[],
            "levels":[]
        }


    return analyzer(
        data,
        symbol
    )
