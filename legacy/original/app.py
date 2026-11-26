from pathlib import Path
import os, time, json, tempfile
from datetime import datetime, timezone
from dotenv import load_dotenv
import gradio as gr
from derja_lab import engines as e

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT/'.env')


def transcribe_audio(audio, asr, language):
    start = time.perf_counter()
    try:
        text = e.transcribe(audio, asr, language)
        return text, {'asr':asr,'stt_seconds':round(time.perf_counter()-start,3),'original_transcript':text}, 'Transcribed. Edit the text if needed, then Send.'
    except Exception as exc:
        return gr.skip(), {}, f'Transcription failed: {exc}'


def send(question, history, logs, asr_info, llm, language, style, temperature, max_tokens, groq_model, voice, reference, ref_text, consent):
    question = (question or '').strip()
    if not question or len(question)>4000:
        return history, logs, None, '', gr.skip(), 'Enter a message of 1–4,000 characters.', gr.skip(), asr_info
    start=time.perf_counter()
    try:
        reply=e.chat(llm,history,question,language,style,temperature,int(max_tokens),groq_model)
    except Exception as exc:
        return history, logs, None, '', gr.skip(), f'Chat failed: {exc}', gr.skip(), asr_info
    info=dict(asr_info or {})
    info.update({'llm':llm,'model_id':(groq_model.strip() or os.getenv('GROQ_MODEL','qwen/qwen3.8-27b')) if llm=='Groq (cloud)' else (e.gemini_model_id() if llm=='Gemini (cloud)' else e.LLMS[llm]), 'language':language,'style':style,'temperature':temperature,'max_tokens':e.gemini_token_budget() if llm=='Gemini (cloud)' else int(max_tokens),'llm_seconds':round(time.perf_counter()-start,3),'voice':voice,'tts_seconds':None})
    audio=None; status='Answer generated.'
    if voice!=e.VOICES[0]:
        if style=='Arabizi' or language not in ('Tunisian (Derja)','Arabic (MSA)'):
            status='Answer generated. Tunisian TTS expects Arabic-script text; edit speech text and use Speak.'
        else:
            t=time.perf_counter()
            try:
                audio=e.synthesize(reply,voice,reference,ref_text,consent)
                info['tts_seconds']=round(time.perf_counter()-t,3)
            except Exception as exc: status=f'Answer generated; voice failed: {exc}'
    log={'timestamp':datetime.now(timezone.utc).isoformat(),'question':question,'answer':reply,'metrics':info,'ratings':None,'notes':''}
    newhistory=history+[{'role':'user','content':question},{'role':'assistant','content':reply}]
    return newhistory, logs+[log], audio, reply, '', status, info, {}


def speak(text,voice,reference,ref_text,consent,logs):
    if not text or not text.strip(): return None,'Enter text to synthesize.',logs,gr.skip()
    if voice==e.VOICES[0]: return None,'Select a voice engine first.',logs,gr.skip()
    t=time.perf_counter()
    try:
        audio=e.synthesize(text.strip(),voice,reference,ref_text,consent)
        elapsed=round(time.perf_counter()-t,3)
        info={'voice':voice,'tts_seconds':elapsed,'speech_text':text.strip()}
        # Attach regenerated audio metadata to last turn; standalone tests also remain visible.
        if logs:
            logs=[*logs[:-1],{**logs[-1],'metrics':{**logs[-1]['metrics'],**info}}]
        return audio,f'Voice generated in {elapsed}s.',logs,logs[-1]['metrics'] if logs else info
    except Exception as exc: return None,f'Voice failed: {exc}',logs,gr.skip()


def rate(logs, understanding, correctness, dialect, naturalness, context, notes):
    if not logs: return logs,'Send a message before rating.'
    vals={'understanding':understanding,'correctness':correctness,'dialect':dialect,'voice_naturalness':naturalness,'context':context}
    vals={k:(None if v==0 else int(v)) for k,v in vals.items()}
    return [*logs[:-1],{**logs[-1],'ratings':vals,'notes':notes}], 'Rating saved for latest answer.'


def export(logs):
    folder=ROOT/'outputs'; folder.mkdir(exist_ok=True)
    fd,path=tempfile.mkstemp(prefix='evaluation_',suffix='.json',dir=folder); os.close(fd)
    Path(path).write_text(json.dumps({'schema_version':1,'turns':logs},ensure_ascii=False,indent=2),encoding='utf-8')
    return path


def clear(): return [],[],None,'','', 'New conversation.',{}, {}, None


def build():
    with gr.Blocks(title='Derja AI Lab') as demo:
        gr.Markdown('# Derja AI Lab | عسلامة\n**Tunisian voice & text model playground** · Personal research prototype. Local by default. No RAG. No automatic cloud fallback.')
        history=gr.State([]); logs=gr.State([]); asr_info=gr.State({})
        with gr.Row():
            with gr.Column(scale=3):
                chatbot=gr.Chatbot(label='Conversation',height=430)
                recording=gr.Audio(sources=['microphone','upload'],type='filepath',label='Record your question or upload audio')
                trans=gr.Button('1. Transcribe audio')
                question=gr.Textbox(label='2. Type a question or review/edit the transcript',lines=3,placeholder='3aslema, chnowa a7welek?')
                with gr.Row():
                    submit=gr.Button('3. Send',variant='primary'); reset=gr.Button('New conversation')
                status=gr.Textbox(label='Status',interactive=False,lines=3)
                speech_text=gr.Textbox(label='Speech text (editable)',lines=3)
                speak_btn=gr.Button('Speak / regenerate voice')
                playback=gr.Audio(label='Generated answer',type='filepath',interactive=False)
            with gr.Column(scale=2):
                llm=gr.Dropdown(list(e.LLMS),value='Labess 7B (local)',label='Language model')
                groq_model=gr.Textbox(value=os.getenv('GROQ_MODEL','qwen/qwen3.8-27b'),label='Groq model ID (only cloud mode)')
                gr.Markdown('Cloud mode sends text and recent conversation to the selected provider (Groq or Gemini). Audio stays local. Gemini model ID and total generation budget are set in .env (GEMINI_MAX_OUTPUT_TOKENS, default 8192, includes reasoning). The token slider applies to other models. Check provider plan before use.')
                asr=gr.Dropdown(list(e.ASRS),value='Whisper Tunisian INT8',label='Speech recognition')
                language=gr.Dropdown(list(e.LANGS),value='Tunisian (Derja)',label='Speech input hint / response language')
                style=gr.Radio(['Arabic script','Arabizi'],value='Arabic script',label='Tunisian writing style')
                temperature=gr.Slider(0,1,step=.1,value=.5,label='Temperature')
                max_tokens=gr.Slider(64,1024,step=32,value=256,label='Maximum output tokens (non-Gemini models)')
                voice=gr.Dropdown(e.VOICES,value=e.VOICES[0],label='Voice synthesis (install optional environment first)')
                reference=gr.Audio(sources=['microphone','upload'],type='filepath',label='Your authorized voice reference (6–15 sec recommended)')
                ref_text=gr.Textbox(label='Exact transcript of reference (required for SILMA)')
                consent=gr.Checkbox(label='I own this voice or have permission to synthesize it',value=False)
                metrics=gr.JSON(label='Latest turn metrics (includes cold-start time)')
        with gr.Accordion('Evaluate and export',open=True):
            gr.Markdown('Score the latest answer from 1 to 5. Set 0 for not evaluated. Export includes question, answer, models, timings and ratings; no raw audio or keys.')
            with gr.Row():
                ratings=[gr.Slider(0,5,step=1,value=0,label=label) for label in ['Understanding','Correctness','Derja authenticity','Voice naturalness','Context']]
            notes=gr.Textbox(label='Notes')
            save=gr.Button('Save rating'); export_btn=gr.Button('Export evaluation JSON'); file=gr.File(label='Export',interactive=False)
        gr.Examples(examples=[['عسلامة، شنية أحوالك؟'],['N7eb na3ref kifech nabda projet sghir fi Tounes.'],['ما قلتلكش تبدل ال rendez-vous، قلتلك أكدلي عليه.']],inputs=[question])
        trans.click(transcribe_audio,[recording,asr,language],[question,asr_info,status])
        inputs=[question,history,logs,asr_info,llm,language,style,temperature,max_tokens,groq_model,voice,reference,ref_text,consent]
        outputs=[history,logs,playback,speech_text,question,status,metrics,asr_info]
        # Chatbot mirrors history after completion.
        submit.click(send,inputs,outputs,concurrency_id='models',concurrency_limit=1).then(lambda h:h,history,chatbot)
        question.submit(send,inputs,outputs,concurrency_id='models',concurrency_limit=1).then(lambda h:h,history,chatbot)
        speak_btn.click(speak,[speech_text,voice,reference,ref_text,consent,logs],[playback,status,logs,metrics],concurrency_id='models',concurrency_limit=1)
        save.click(rate,[logs,*ratings,notes],[logs,status]); export_btn.click(export,logs,file)
        reset.click(clear,None,[history,logs,playback,speech_text,question,status,metrics,asr_info,recording]).then(lambda h:h,history,chatbot)
    return demo

if __name__=='__main__':
    build().queue(default_concurrency_limit=1).launch(server_name='127.0.0.1',server_port=7860,share=False,inbrowser=True,show_error=False)
