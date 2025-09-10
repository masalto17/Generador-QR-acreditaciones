import os
import csv
import zipfile
from flask import Flask, request, render_template, send_file, after_this_request
from PIL import Image
import qrcode
import shutil

# 1. Configuración inicial de Flask
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
GENERATED_FOLDER = 'generated_qrs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['GENERATED_FOLDER'] = GENERATED_FOLDER

# Asegurarse de que las carpetas existan
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)

# 2. Definir la ruta principal que muestra la página web
@app.route('/')
def index():
    # render_template busca un archivo en la carpeta 'templates'
    return render_template('index.html')

# 3. Definir la ruta que procesa los archivos y genera los QR
@app.route('/generate', methods=['POST'])
def generate():
    # Recibir los archivos del formulario
    csv_file = request.files['csv_file']
    logo_file = request.files['logo_file']

    if not csv_file or not logo_file:
        return "Error: Faltan archivos. Por favor, sube ambos.", 400

    # Guardar los archivos subidos temporalmente
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_file.filename)
    logo_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_file.filename)
    csv_file.save(csv_path)
    logo_file.save(logo_path)

    # Limpiar la carpeta de QRs generados anteriormente
    shutil.rmtree(app.config['GENERATED_FOLDER'])
    os.makedirs(app.config['GENERATED_FOLDER'])

    try:
        # --- Lógica de generación de QR (la que ya conoces) ---
        logo = Image.open(logo_path)
        
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader) # Saltar cabecera
            for row in reader:
                dato = row[0]
                nombre_archivo = row[1]
                
                qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
                qr.add_data(dato)
                qr.make(fit=True)
                
                img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
                
                qr_width, qr_height = img_qr.size
                logo_max_size = qr_height // 4
                logo.thumbnail((logo_max_size, logo_max_size))
                
                pos_x = (qr_width - logo.width) // 2
                pos_y = (qr_height - logo.height) // 2
                
                img_qr.paste(logo, (pos_x, pos_y), mask=logo if logo.mode == 'RGBA' else None)
                
                # Guardar el QR en su carpeta
                img_qr.save(os.path.join(app.config['GENERATED_FOLDER'], nombre_archivo))

        # --- Comprimir los QR en un archivo Zip ---
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'codigos_qr.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(app.config['GENERATED_FOLDER']):
                for file in files:
                    zipf.write(os.path.join(root, file), arcname=file)
        
        # --- Limpieza de archivos temporales ---
        @after_this_request
        def cleanup(response):
            try:
                os.remove(csv_path)
                os.remove(logo_path)
                os.remove(zip_path)
                shutil.rmtree(app.config['GENERATED_FOLDER'])
            except Exception as e:
                print(f"Error en la limpieza: {e}")
            return response
            
        # Enviar el archivo zip para descarga
        return send_file(zip_path, as_attachment=True)

    except Exception as e:
        return f"Ocurrió un error: {e}", 500

# 4. Iniciar la aplicación
if __name__ == '__main__':
    app.run(debug=True)