from .core import normalize,numbers
import re

def edit(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        nxt=[i]
        for j,y in enumerate(b,1): nxt.append(min(nxt[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=nxt
    return row[-1]

def scores(ref,hyp):
    a,b=normalize(ref),normalize(hyp); aw,bw=a.split(),b.split()
    return {'word_edits':edit(aw,bw),'reference_words':len(aw),'char_edits':edit(a,b),'reference_chars':len(a),'wer':edit(aw,bw)/len(aw) if aw else None,'cer':edit(a,b)/len(a) if a else None,'numbers_exact':numbers(a)==numbers(b)}
