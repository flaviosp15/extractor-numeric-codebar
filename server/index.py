from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from PIL import Image
try:
    import pymupdf
except ImportError:
    import fitz as pymupdf
import pytesseract
import io
import os
import re
import tempfile
from typing import List, Dict, Optional
import time
import logging
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.reload = os.getenv("RELOAD", "false").lower() == "true"
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.workers = int(os.getenv("WORKERS", "1"))
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", "10485760"))
        self.tesseract_cmd = os.getenv("TESSERACT_CMD", "C:\\Program Files\\Tesseract-OCR\\tesseract.exe")

        if self.environment == "production":
            self.allowed_origins = os.getenv("ALLOWED_ORIGINS")
        else:
            self.allowed_origins = ["*"]

settings = Settings()

logging.basicConfig(
    level=logging.INFO if settings.environment == "production" else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

app = FastAPI(
    title="PDF Barcode Extractor API",
    description="API para extração de códigos de barras de arquivos PDF",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.environment == "production":
    app.add_middleware(GZipMiddleware, minimum_size=1000)

if settings.environment == "production":
    frontend_path = "/app/client"
else:
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "client")

static_path = os.path.join(frontend_path, 'static')

if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    logger.info(f"Arquivos estáticos montados em: {static_path}")
else:
    logger.warning(f"Pasta de arquivos estáticos não encontrada: {static_path}")

def pdf_to_text(pdf_path: str) -> str:
    """Extrai texto de PDF usando OCR"""
    try:
        if not os.path.exists(pdf_path):
            return f"Erro: Arquivo não encontrado - {pdf_path}"
        
        with pymupdf.open(pdf_path) as pdf_document:
            complete_text = ""
            
            logger.info(f"Processando PDF com {len(pdf_document)} páginas...")
            
            for page_num in range(len(pdf_document)):
                logger.info(f"Processando página {page_num + 1}...")
                
                page = pdf_document.load_page(page_num)
                
                mat = pymupdf.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                
                img_data = pix.tobytes("ppm")
                
                with Image.open(io.BytesIO(img_data)) as img:
                    page_text = pytesseract.image_to_string(img, lang='por')
                    complete_text += f"--- Página {page_num + 1} ---\n{page_text}\n\n"
            
            return complete_text
            
    except Exception as e:
        logger.error(f"Erro no pdf_to_text: {str(e)}")
        return f"Erro ao processar PDF: {str(e)}"

def safe_delete_file(file_path: str, max_retries: int = 5):
    """Tenta excluir um arquivo com múltiplas tentativas"""
    for attempt in range(max_retries):
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Arquivo temporário excluído: {file_path}")
                return True
        except PermissionError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Tentativa {attempt + 1} falhou, aguardando...")
                time.sleep(0.1 * (attempt + 1))
            else:
                logger.error(f"Não foi possível excluir {file_path} após {max_retries} tentativas: {e}")
                return False
        except Exception as e:
            logger.error(f"Erro ao excluir {file_path}: {e}")
            return False
    return False

def process_single_pdf(file_content: bytes, filename: str) -> Dict:
    """Processa um único PDF e retorna resultado"""
    temp_file_path = None
    
    try:
        if len(file_content) > settings.max_file_size:
            raise Exception(f"Arquivo muito grande. Tamanho máximo: {settings.max_file_size // 1024 // 1024}MB")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_content)
            temp_file.flush()
            temp_file_path = temp_file.name
        
        logger.info(f"Processando arquivo: {filename}")
        
        pdf_content = pdf_to_text(temp_file_path)
        
        if pdf_content.startswith("Erro:"):
            raise Exception(pdf_content)
        
        barcode_number = get_barcode_number(pdf_content)
        
        result = {
            "filename": filename,
            "status": "success",
            "barcode_found": barcode_number is not None,
            "barcode": barcode_number,
            "pages_processed": len(pdf_content.split("--- Página")) - 1
        }
        
        if barcode_number:
            logger.info(f"Código encontrado: {barcode_number}")
        else:
            logger.info("Código não encontrado")
            result["barcode"] = "Not Found"
        
        return result
        
    except Exception as e:
        logger.error(f"Erro ao processar {filename}: {str(e)}")
        return {
            "filename": filename,
            "status": "error",
            "error_message": str(e),
            "barcode_found": False,
            "barcode": None,
            "pages_processed": 0
        }
    
    finally:
        if temp_file_path:
            safe_delete_file(temp_file_path)

def get_barcode_number(text: str) -> Optional[str]:
    """Extrai código de barras do texto usando regex"""
    pattern = r'^(\d{5}(\.)?\d{5}(\s)?\d{5}(\.)?\d{6}(\s)?\d{5}(\.)?\d{6}(\s)?\d(\s)?\d{14})$'

    match = re.search(pattern, text, re.MULTILINE)
    
    if match:
        code_bar_number = match.group(0).replace('.', '').replace(' ', '')
        return code_bar_number
    return None

@app.post("/api/extract-barcodes")
async def extract_barcodes(files: List[UploadFile] = File(...)):
    """Endpoint para processar múltiplos arquivos PDF"""
    try:
        max_files = 15

        logger.info(f"Requisição recebida com {len(files)} arquivo(s)")
        
        if not files:
            raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")
        
        if len(files) > max_files:
            raise HTTPException(status_code=400, detail=f"Máximo de {max_files} arquivos por requisição")
        
        results = []
        processed_count = 0
        
        for file in files:
            # Valida se é PDF
            if not file.filename.lower().endswith('.pdf'):
                results.append({
                    "filename": file.filename,
                    "status": "error", 
                    "error_message": "Arquivo não é PDF",
                    "barcode_found": False,
                    "barcode": None,
                    "pages_processed": 0
                })
                continue
            
            try:
                # Lê o conteúdo do arquivo
                content = await file.read()
                
                # Processa o PDF
                result = process_single_pdf(content, file.filename)
                results.append(result)
                
                if result["status"] == "success":
                    processed_count += 1
                
            except Exception as e:
                logger.error(f"Erro ao processar {file.filename}: {str(e)}")
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error_message": f"Erro ao processar arquivo: {str(e)}",
                    "barcode_found": False,
                    "barcode": None,
                    "pages_processed": 0
                })
        
        # Estatísticas gerais
        successful = len([r for r in results if r["status"] == "success" and r["barcode_found"]])
        failed = len([r for r in results if r["status"] == "success" and not r["barcode_found"]])
        errors = len([r for r in results if r["status"] == "error"])
        
        response = {
            "success": True,
            "message": f"Processados {processed_count} arquivo(s)",
            "statistics": {
                "total_files": len(files),
                "successful_extractions": successful,
                "failed_extractions": failed,
                "errors": errors
            },
            "results": results,
            "timestamp": time.time()
        }
        
        logger.info(f"Requisição processada: {successful} sucessos, {failed} falhas, {errors} erros")
        return JSONResponse(content=response)
        
    except Exception as e:
        logger.error(f"Erro interno: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Endpoint de saúde da API"""
    health_info = {
        "status": "healthy",
        "service": "PDF Barcode Extractor",
        "environment": settings.environment,
        "timestamp": time.time()
    }

    if settings.environment == "production":
        try:
            pytesseract.get_tesseract_version()
            health_info["tesseract"] = "ok"
        except Exception as e:
            health_info["tesseract"] = "error"
            health_info["status"] = "degraded"
            
        try:
            import pymupdf
            health_info["pymupdf"] = "ok"
        except Exception as e:
            health_info["pymupdf"] = "error"
            health_info["status"] = "degraded"
    
    return health_info

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve a página HTML do frontend"""
    index_path = os.path.join(frontend_path, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return HTMLResponse("""
        <html>
            <body>
                <h1>PDF Barcode Extractor API</h1>
                <p>Frontend não encontrado. Acesse:</p>
                <ul>
                    <li><a href="/api/health">Health Check</a></li>
                    <li><a href="/docs">Documentação da API</a></li>
                </ul>
                <p>Environment: """ + settings.environment + """</p>
            </body>
        </html>
        """)

if __name__ == "__main__":
    logger.info(f"Iniciando servidor em modo {settings.environment}")
    logger.info(f"Host: {settings.host}, Port: {settings.port}")
    logger.info(f"Debug: {settings.debug}, Reload: {settings.reload}")
    
    import uvicorn
    
    uvicorn.run(
        "index:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info" if settings.environment == "production" else "debug"
    )