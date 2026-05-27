import os
import time
import requests
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

API_URL = "http://localhost:8000/api/audit-pdf"
INCOMING_DIR = os.path.join(os.path.dirname(__file__), "incoming_invoices")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "processed_invoices")

class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            print(f"📄 Nuevo PDF detectado: {event.src_path}")
            # Esperar un poco para asegurar que el archivo terminó de copiarse
            time.sleep(1)
            self.process_pdf(event.src_path)

    def process_pdf(self, file_path):
        filename = os.path.basename(file_path)
        print(f"⏳ Procesando {filename} con IA...")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f, 'application/pdf')}
                response = requests.post(API_URL, files=files)
            
            if response.status_code == 200:
                print(f"✅ Auditoría completada con éxito para {filename}")
                self.move_file(file_path, filename)
            else:
                print(f"❌ Error al procesar {filename}: {response.text}")
        except Exception as e:
            print(f"⚠️ Excepción al conectar con la API: {e}")

    def move_file(self, file_path, filename):
        dest_path = os.path.join(PROCESSED_DIR, filename)
        try:
            shutil.move(file_path, dest_path)
            print(f"📁 Movido a {PROCESSED_DIR}")
        except Exception as e:
            print(f"⚠️ No se pudo mover el archivo: {e}")

if __name__ == "__main__":
    os.makedirs(INCOMING_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, INCOMING_DIR, recursive=False)
    
    print(f"👁️‍🗨️ Watchdog iniciado. Escuchando en: {INCOMING_DIR}")
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
