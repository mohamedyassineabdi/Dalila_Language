import json
from pathlib import Path
# New, authored drafts. Not human validation or blind samples.
raw='''aeb|availability|فمّاش مقسم فارغ في سيدي بوزيد؟|Sidi Bouzid||
aeb|price|billehi soum el mètre fi gabes b9addech?|Gabès||
aeb|documents|شنية les documents اللازمة للدوسي متاعي؟|||
aeb|procedure|كيفاش نعمل باش نودع مطلب متاع مصنع؟|||
aeb|surface|نحب 1250 m² موش 2500 في القيروان|Kairouan|موش|
aeb|deadline|wa9tech e5er délai bech n9adem?| ||
aeb|incentives|فما إعفاء جبائي للمشروع الجديد؟|||
aeb|clarify|فسّرلي أكثر شنوة تقصد؟|||
aeb|availability|n7eb na3ref ken fama blasa dispo fi nebel|Nabeul||
aeb|price|قداش tarif متاع المتر في منوبة؟|Manouba||
aeb|documents|chneya awra9 elli lezemni lel dossier?|||
aeb|procedure|bahi kifech nabda les démarches?|||
aeb|surface|moch 900 m2 n7eb 1800 m2 fi Sfax|Sfax|moch|
aeb|deadline|نهار 3 جانفي ينجم يكون آخر أجل؟|||
aeb|incentives|tnajjem t9olli chnowa les subventions?|||
aeb|clarify|ma fhemtch, fasserli bchwaya||ma fhemtch|
aeb|availability|ما فماش terrain disponible في قابس؟|Gabès|ما فماش|
aeb|price|السوم بالدينار ولا بالأورو في زغوان؟|Zaghouan||
aeb|documents|ما نحبش نبعث dossier ناقص، شنوة الأوراق؟||ما نحبش|
aeb|surface|n7eb 2.5 ha mouch 25 ha| |mouch|
aeb|surface|مساحة ٩٠٠ متر مربع موش ١٩٠٠ في نابل|Nabeul|موش|
aeb|deadline|ينجم الواحد يقدم قبل 31/12؟|||
aeb|incentives|شنيا les aides pour projet industriel?|||
aeb|availability|famma lot vacant fi ben 3arous?|Ben Arous||
ar|availability|هل توجد قطعة أرض صناعية متاحة في باجة؟|Béja||
ar|price|أريد معرفة تكلفة المتر في صفاقس|Sfax||
ar|documents|ما المستندات التي يجب تقديمها؟|||
ar|procedure|كيفية إيداع طلب تخصيص أرض؟|||
ar|surface|أرغب في مساحة 600 متر مربع وليس 1600|||
ar|deadline|ما هو تاريخ انتهاء فترة التقديم؟|||
ar|incentives|هل توجد حوافز ضريبية للمستثمر؟|||
ar|clarify|يرجى توضيح المقصود بالطلب|||
fr|availability|Reste-t-il des parcelles disponibles à Bizerte ?|Bizerte||
fr|price|Quel est le tarif au mètre carré à Sousse ?|Sousse||
fr|documents|Quels justificatifs dois-je joindre au dossier ?|||
fr|procedure|Comment déposer ma demande de terrain industriel ?|||
fr|surface|Je veux 1250 m², pas 2500 m² à Zaghouan.|Zaghouan|pas|
fr|deadline|Quelle est la date limite de dépôt ?|||
fr|incentives|Quelles aides fiscales existent pour une usine ?|||
fr|clarify|Pouvez-vous préciser ce que cela signifie ?|||
en|availability|Are any industrial lots still vacant in Tunis?|Tunis||
en|price|What is the cost per square metre in Sfax?|Sfax||
en|documents|Which supporting documents do I need?|||
en|procedure|How can I apply for a plot?|||
en|surface|I want 1200 m², not 2200, in Nabeul.|Nabeul|not|
en|deadline|When is the closing date for applications?|||
en|incentives|Are there grants for new manufacturers?|||
en|clarify|What do you mean by that?|||
arq|availability|واش كاين أرض متوفرة في بنزرت؟|Bizerte||
arq|price|شحال السعر للمتر في سوسة؟|Sousse||
arq|documents|واش هما الوثائق لي نديهم؟|||
arq|procedure|راني حاب نعرف كيفاش ندير الطلب|||
arq|surface|نحب 800 متر مربع ماشي 1800||ماشي|
arq|deadline|وقتاش آخر أجل باش ندفع الملف؟|||
arq|incentives|كاين إعفاءات ضريبية ولا لا؟||لا|
arq|clarify|واش تقصد؟ فسرلي شوية|||
ayl|availability|فيه أرض متوفرة في نابل؟ نبي نعرف|Nabeul||
ayl|price|نبي نعرف سعر المتر في بنزرت|Bizerte||
ayl|documents|شن الأوراق اللي لازم نجيبهن؟|||
ayl|procedure|نبي نقدم على أرض كيف ندير؟|||
ayl|surface|نبي 1200 متر مربع مش 2000||مش|
ayl|deadline|إمتى آخر موعد للتقديم؟|||
ayl|incentives|فيه حوافز للمصانع الجديدة؟|||
ayl|clarify|شن تقصد؟ وضحلي بالله|||
de|availability|Sind in Tunis noch Grundstücke verfügbar?|Tunis||
de|price|Wie hoch ist der Preis pro Quadratmeter in Sfax?|Sfax||
de|documents|Welche Dokumente muss ich mitbringen?|||
de|procedure|Wie kann ich ein Industriegrundstück beantragen?|||
de|surface|Ich möchte 1200 m², nicht 2000 m².| |nicht|
de|deadline|Wann ist die Frist für den Antrag?|||
de|incentives|Gibt es Fördermittel für neue Fabriken?|||
de|clarify|Was bedeutet das genau?|||
tr|availability|Sfax'ta boş sanayi arsası var mı?|Sfax||
tr|price|Bizerte'de metrekare fiyatı nedir?|Bizerte||
tr|documents|Başvuru için hangi belgeler gerekli?|||
tr|procedure|Sanayi arsası için nasıl başvuru yapabilirim?|||
tr|surface|2000 değil, 1200 metrekare istiyorum.||değil|
tr|deadline|Son başvuru tarihi nedir?|||
tr|incentives|Yeni fabrikalara teşvik var mı?|||
tr|clarify|Bunu biraz açıklar mısınız?|||'''
rows=[]
for i,l in enumerate(raw.splitlines(),1):
 lang,intent,text,places,neg,_=l.split('|'); rows.append(dict(id=f's{i:03}',language=lang,intent=intent,text=text,places=[v.strip() for v in places.split(',') if v.strip()],negation=[v.strip() for v in neg.split(',') if v.strip()],split='eval',provenance='synthetic_draft',review_status='unreviewed'))
Path(__file__).with_name('stress_cases.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
