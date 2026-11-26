import json
from pathlib import Path
# Draft examples authored for this lab, not independently validated or human recordings.
# Each line: language | split | intent | text. No AFI facts are asserted.
raw = '''aeb|dev|availability|فما مقاسم فارغة في بن عروس؟
aeb|dev|price|قداش سوم المتر في المنطقة الصناعية؟
aeb|dev|documents|شنوة الأوراق اللازمة باش نقدّم مطلب؟
aeb|dev|procedure|كيفاش ناخذ قطعة أرض من الوكالة؟
aeb|dev|surface|نحب مقسم مساحتو 500 متر مربع
aeb|dev|deadline|وقتاش آخر أجل للتسجيل؟
aeb|dev|availability|fama terrain disponible fi bizerte?
aeb|dev|price|9addech soum el mètre carré?
aeb|dev|documents|chnowa les papiers elli lezemni?
aeb|dev|procedure|kifech na3mel demande mta3 terrain?
aeb|dev|surface|n7eb terrain 1000 m²
aeb|dev|deadline|wa9tech deadline mta3 dépôt?
aeb|dev|incentives|شنوة الامتيازات للاستثمار؟
aeb|dev|clarify|ما فهمتش، وضحلي أكثر
aeb|dev|incentives|fama avantages fiscaux lel investissement?
aeb|dev|clarify|ma fhemtch chnowa ta9sed
aeb|eval|availability|بالله فما بلاصة شاغرة في زغوان؟
aeb|eval|price|بقداش المتر في سوسة موش في صفاقس؟
aeb|eval|documents|شنية الوثايق اللي نجيبهم معايا للـ dossier؟
aeb|eval|procedure|نحب نعمل usine، منين نبدأ؟
aeb|eval|surface|ما نحبش 2000 متر مربع، نحب 750 m²
aeb|eval|deadline|ينجم الواحد يودع المطلب قبل 15 ديسمبر؟
aeb|eval|availability|3aslema, famma lot disponible fi Mghira?
aeb|eval|price|b9addech el prix unitaire fi Sfax?
aeb|eval|documents|chneya les pièces justificatives elli na7tajhom?
aeb|eval|procedure|najem na3mel réservation en ligne walla le?
aeb|eval|surface|n7eb 800 m2 moch 1800
aeb|eval|deadline|emta nsakker dossier?
aeb|eval|incentives|فمّا تشجيعات جبائية للصناعيين؟
aeb|eval|clarify|و بالنسبة للأخرى؟
aeb|eval|incentives|chneya el aides lel projet jdid?
aeb|eval|clarify|w heki 9addech?
ar|dev|availability|هل توجد قطع صناعية متاحة؟
ar|dev|price|ما سعر المتر المربع؟
ar|dev|documents|ما الوثائق المطلوبة؟
ar|dev|procedure|كيف أقدم طلب تخصيص أرض صناعية؟
ar|dev|surface|أبحث عن مساحة 500 متر مربع
a r|dev|deadline|ما الموعد النهائي لإيداع الطلب؟
ar|dev|incentives|ما الحوافز الاستثمارية؟
ar|dev|clarify|يرجى توضيح المقصود
a r|eval|availability|هل تتوفر أراض صناعية في بنزرت؟
ar|eval|price|كم تبلغ تكلفة القطعة؟
ar|eval|documents|ما المستندات اللازمة لإكمال الملف؟
ar|eval|procedure|أريد معرفة إجراءات إنشاء مصنع
a r|eval|surface|أحتاج إلى 750 مترا مربعا وليس 2000
a r|eval|deadline|هل يمكن التسجيل قبل 15 ديسمبر؟
ar|eval|incentives|هل توجد إعفاءات ضريبية؟
ar|eval|clarify|وماذا عن المنطقة الأخرى؟
fr|dev|availability|Y a-t-il des lots disponibles ?
fr|dev|price|Quel est le prix au mètre carré ?
fr|dev|documents|Quels documents faut-il fournir ?
fr|dev|procedure|Comment déposer une demande de terrain industriel ?
fr|dev|surface|Je cherche une parcelle de 500 m².
fr|dev|deadline|Quelle est la date limite de dépôt ?
fr|dev|incentives|Quelles sont les incitations à l’investissement ?
fr|dev|clarify|Pouvez-vous préciser votre question ?
fr|eval|availability|Reste-t-il des terrains libres à Bizerte ?
fr|eval|price|Combien coûte un lot à Sfax ?
fr|eval|documents|Quelles pièces joindre au dossier ?
fr|eval|procedure|Par où commencer pour ouvrir une usine ?
fr|eval|surface|Je veux 750 m², pas 2000.
fr|eval|deadline|Puis-je déposer le dossier avant le 15 décembre ?
fr|eval|incentives|Existe-t-il des avantages fiscaux ?
fr|eval|clarify|Et pour l’autre zone ?
en|dev|availability|Are industrial plots available?
en|dev|price|What is the price per square meter?
en|dev|documents|Which documents are required?
en|dev|procedure|How do I apply for industrial land?
en|dev|surface|I need a 500 square meter plot.
en|dev|deadline|What is the application deadline?
en|dev|incentives|What investment incentives are available?
en|dev|clarify|Could you clarify what you mean?
en|eval|availability|Is there any vacant land in Bizerte?
en|eval|price|How much does a plot in Sfax cost?
en|eval|documents|What paperwork should I bring?
en|eval|procedure|Where do I start if I want to build a factory?
en|eval|surface|I want 750 m², not 2000.
en|eval|deadline|Can I submit before December 15?
en|eval|incentives|Are there any tax breaks?
en|eval|clarify|What about the other area?
arq|dev|availability|كاين قطع أرض صناعية فارغين؟
arq|dev|price|شحال يسوى المتر المربع؟
arq|dev|documents|واش من ورق لازم ندفع؟
arq|dev|procedure|كيفاش ندير باش نطلب أرض صناعية؟
arq|dev|surface|راني حاب قطعة فيها 500 متر مربع
a rq|dev|deadline|وقتاش يسال التسجيل؟
arq|dev|incentives|كاين تسهيلات للمستثمرين؟
arq|dev|clarify|ما فهمتش واش تقصد
a rq|eval|availability|واش مازال كاين terrain في بنزرت؟
arq|eval|price|بشحال هذي الأرض في صفاقس؟
arq|eval|documents|واش لازملي في الدوسي؟
arq|eval|procedure|حاب نفتح مصنع كيفاش نبدا؟
arq|eval|surface|راني باغي 750 متر ماشي 2000
a rq|eval|deadline|نقدر ندفع قبل 15 ديسمبر؟
arq|eval|incentives|كاين إعفاءات من الضريبة ولا والو؟
arq|eval|clarify|و هذيك الأخرى؟
ayl|dev|availability|فيه أراضي صناعية فاضية؟
ayl|dev|price|بكم سعر المتر هني؟
ayl|dev|documents|شن الأوراق اللي نبيها؟
ayl|dev|procedure|كيف ندير باش نطلب أرض؟
ayl|dev|surface|نبي قطعة 500 متر مربع
a yl|dev|deadline|إمتى يقفل التقديم؟
ayl|dev|incentives|فيه مزايا للمستثمرين؟
ayl|dev|clarify|شن تقصد بالله؟
ayl|eval|availability|فيه قطعة متوفرة في بنزرت توا؟
ayl|eval|price|بكم تجيني الأرض في صفاقس؟
ayl|eval|documents|شن المستندات اللي نجيبها معاي؟
ayl|eval|procedure|نبي نفتح مصنع شن ندير أول حاجة؟
ayl|eval|surface|نبي 750 متر مش 2000
a yl|eval|deadline|نقدر نقدم قبل 15 ديسمبر؟
ayl|eval|incentives|فيه تخفيضات ضريبية للمشروع؟
ayl|eval|clarify|والمنطقة الثانية كيف؟
de|dev|availability|Sind Industriegrundstücke verfügbar?
de|dev|price|Wie hoch ist der Quadratmeterpreis?
de|dev|documents|Welche Unterlagen werden benötigt?
de|dev|procedure|Wie beantrage ich ein Industriegrundstück?
de|dev|surface|Ich suche ein Grundstück mit 500 Quadratmetern.
de|dev|deadline|Wann endet die Antragsfrist?
de|dev|incentives|Welche Investitionsanreize gibt es?
de|dev|clarify|Können Sie das genauer erklären?
de|eval|availability|Gibt es noch freie Flächen in Bizerte?
de|eval|price|Was kostet ein Grundstück in Sfax?
de|eval|documents|Welche Papiere muss ich einreichen?
de|eval|procedure|Wie fange ich mit dem Bau einer Fabrik an?
de|eval|surface|Ich brauche 750 m², nicht 2000.
de|eval|deadline|Kann ich den Antrag vor dem 15. Dezember abgeben?
de|eval|incentives|Gibt es Steuervergünstigungen?
de|eval|clarify|Und was ist mit dem anderen Gebiet?
tr|dev|availability|Sanayi arsası mevcut mu?
tr|dev|price|Metrekare fiyatı ne kadar?
tr|dev|documents|Hangi belgeler gerekiyor?
tr|dev|procedure|Sanayi arsasına nasıl başvurabilirim?
tr|dev|surface|500 metrekare arsa arıyorum.
tr|dev|deadline|Son başvuru tarihi ne zaman?
tr|dev|incentives|Yatırım teşvikleri nelerdir?
tr|dev|clarify|Ne demek istediğinizi açıklar mısınız?
tr|eval|availability|Bizerte'de boş arsa var mı?
tr|eval|price|Sfax'ta bir arsa kaç para?
tr|eval|documents|Dosyaya hangi evrakları eklemeliyim?
tr|eval|procedure|Fabrika açmak için nereden başlamalıyım?
tr|eval|surface|2000 değil 750 m² istiyorum.
tr|eval|deadline|15 Aralık'tan önce başvurabilir miyim?
tr|eval|incentives|Vergi indirimi var mı?
tr|eval|clarify|Peki diğer bölge?'''
rows=[]
for i,line in enumerate(raw.splitlines()):
    lang,split,intent,t=line.split('|',3); lang=lang.replace(' ','')
    rows.append(dict(id=f't{i+1:03}',language=lang,split=split,intent=intent,text=t,provenance='synthetic_draft',review_status='unreviewed'))
Path(__file__).with_name('text_cases.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
