"""Generate matched Tunisian prompts for native-speaker listening tests."""
import argparse
import json
import os
from pathlib import Path
import time
from dalila.tunisian_worker import load, generate

SAMPLES=[
    ("greeting","عسلامة! لاباس؟ كيفاش نجم نعاونك اليوم؟"),
    ("project","إي، نجم نعاونك. شنوة نوع المشروع اللي تحب تعملو؟"),
    ("question","بالله قُلّي، إنتي منين؟ وشنوة تحب تعرف بالضبط؟"),
    ("negation","ما نحبّش نبدّل المطلب، نحب نكمّل الإجراءات."),
    ("codeswitch","تنجم تبعثلي le dossier par email، وبعد نتفاهمو على la réservation."),
    ("location","نحب نسأل على المنطقة الصناعية في بنزرت وصفاقس."),
    ("numbers","المساحة 750 متر مربّع، موش 2000."),
]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=Path("outputs/tunisian_voice_eval"))
    args=parser.parse_args()
    if os.getenv("DALILA_TUNISIAN_RESEARCH")!="1":
        raise SystemExit("Enable noncommercial research mode explicitly.")
    args.out.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    model=load()
    report={"model":"k2-fsa/OmniVoice","language":"aeb",
            "load_seconds":round(time.perf_counter()-started,3),"samples":[]}
    for name,text in SAMPLES:
        path=args.out/f"{name}.wav"
        result=generate(model,text,path)
        report["samples"].append({"id":name,"text":text,"file":path.name,**result,
                                  "pronunciation_rating":None,"naturalness_rating":None})
        print(name,result,flush=True)
    (args.out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Listen to each recording; successful synthesis is not proof of native pronunciation.")

if __name__=="__main__":
    main()
