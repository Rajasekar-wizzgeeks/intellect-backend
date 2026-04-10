
import json
from datetime import datetime
from fastapi.responses import StreamingResponse
import pandas as pd

class LBscore360Controller:
    def __init__(self):
        self.now = datetime.now()
        self.formatted_date = self.now.strftime("%b %Y")

    async def start_lbscore360_excel_base_job(self, file):
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
        async def event_generator():
            try:
                if not file:
                    payload = {'error': 'File is required.'}
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                files= file if isinstance(file,(list,tuple)) else [file]
                if any(f is None or getattr(f,"file",None) is None for f in files):
                    payload ={"error":"File is required"}
                    yield f"data:{json.dumps(payload)}\n\n"
                    yield "data:[DONE]\n\n"
                    return
                def preprocess_base_sync(__files):
                    def read_excell_file(uploaded_file):
                        uploaded_file.file.seek(0)
                        df=pd.read_excel(uploaded_file.file, engine="openpyxl")
                        df=df.replace([np.nan, np.inf, -np.inf], None)
                        for col in df.columns:
                            if pd.api.types.is_datetime64_any_dtype(df[col]):
                                df[col] = df[col].astype(str)
                        return df.to_dict(orient="records") if df is not None else []
                    file1_data=read_excell_file(__files[0])
                    if not file1_data:
                        return {"error": "No data found in uploaded file."}
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)
     