"""
Servidor para Campus Docente EI-FII
Facultad de Ingeniería Industrial - Universidad de Guayaquil
Cátedra de Emprendimiento e Innovación
Docente & Administrador: Econ. Janio Cerezo Piedrahita, Mgs.
"""

import http.server
import socketserver
import webbrowser
import os
import sys
import json
import re
from datetime import datetime

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(DIRECTORY, "submissions_db.json")

def get_free_port(start_port=8090):
    import socket
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    return 8090

PORT = int(os.environ.get("PORT", get_free_port(8090)))

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_db(db):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error al guardar base de datos:", e)

def normalize_words(text):
    text = re.sub(r'[^\w\s]', '', text.lower())
    return set(text.split())

def get_ngrams(text, n=3):
    text = re.sub(r'[^\w\s]', '', text.lower())
    words = text.split()
    return set([' '.join(words[i:i+n]) for i in range(len(words)-n+1)])

def calculate_similarity(text1, text2):
    w1 = normalize_words(text1)
    w2 = normalize_words(text2)
    if not w1 or not w2:
        return 0.0

    # Jaccard de palabras individuales
    inter_words = len(w1.intersection(w2))
    union_words = len(w1.union(w2))
    word_sim = (inter_words / union_words) * 100 if union_words > 0 else 0.0

    # N-gramas de 3 palabras (secuencias)
    ng1 = get_ngrams(text1, 3)
    ng2 = get_ngrams(text2, 3)
    if ng1 and ng2:
        inter_ng = len(ng1.intersection(ng2))
        union_ng = len(ng1.union(ng2))
        ngram_sim = (inter_ng / union_ng) * 100 if union_ng > 0 else 0.0
    else:
        ngram_sim = 0.0

    # Si hay copia de frases largas o alto solapamiento de palabras
    return round(max(word_sim, (0.4 * word_sim + 0.6 * ngram_sim)), 1)

class EIFIIServerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_POST(self):
        if self.path == "/api/check-similarity":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            topic_id = str(data.get("topicId", ""))
            student_name = data.get("studentName", "Estudiante Desconocido").strip()
            student_email = data.get("studentEmail", "").strip().lower()
            team_name = data.get("team", "Equipo Sin Nombre").strip()
            paralelo = data.get("paralelo", "IND").strip()
            new_text = data.get("text", "").strip()

            db = load_db()
            topic_submissions = db.get(topic_id, [])

            max_sim = 0.0
            matched_entry = None

            # Comparar contra todas las respuestas previas de otros estudiantes
            for entry in topic_submissions:
                # Omitir si es el mismo estudiante actualizando su propia respuesta
                if entry.get("studentEmail", "").lower() == student_email and student_email:
                    continue
                if entry.get("studentName", "").lower() == student_name.lower() and student_name:
                    continue

                sim = calculate_similarity(new_text, entry.get("text", ""))
                if sim > max_sim:
                    max_sim = sim
                    matched_entry = entry

            # UMBRAL ANTIFRAUDE: Si supera el 55% de coincidencia textual
            SIMILARITY_THRESHOLD = 55.0

            if max_sim >= SIMILARITY_THRESHOLD and matched_entry:
                # REGISTRAR EVENTO DE AUDITORÍA POR FRAUDE DETECTADO
                audit_file = os.path.join(DIRECTORY, "antifraud_audit_log.json")
                audit_log = []
                if os.path.exists(audit_file):
                    try:
                        with open(audit_file, "r", encoding="utf-8") as af:
                            audit_log = json.load(af)
                    except Exception:
                        audit_log = []

                audit_event = {
                    "id": f"fraud-{len(audit_log) + 1}",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "topicId": topic_id,
                    "attemptedStudent": student_name,
                    "attemptedEmail": student_email,
                    "attemptedTeam": team_name,
                    "paralelo": paralelo,
                    "similarity": max_sim,
                    "copiedFromStudent": matched_entry.get("studentName", "Otro Estudiante"),
                    "copiedFromTeam": matched_entry.get("team", "Otro Equipo"),
                    "originalDate": matched_entry.get("timestamp", ""),
                    "status": "BLOQUEADO"
                }
                audit_log.append(audit_event)
                try:
                    with open(audit_file, "w", encoding="utf-8") as af:
                        json.dump(audit_log, af, ensure_ascii=False, indent=2)
                except Exception as e:
                    print("Error al guardar audit log:", e)

                response = {
                    "allowed": False,
                    "similarity": max_sim,
                    "matchedStudent": matched_entry.get("studentName", "Otro Estudiante"),
                    "matchedTeam": matched_entry.get("team", "Otro Equipo"),
                    "matchedParalelo": matched_entry.get("paralelo", "Paralelo FII"),
                    "matchedDate": matched_entry.get("timestamp", ""),
                    "message": f"Coincidencia del {max_sim}% detectada con la respuesta de {matched_entry.get('studentName')} ({matched_entry.get('team')}). No se permite guardar respuestas duplicadas o con alta similitud."
                }
            else:
                # Guardar o actualizar la respuesta del estudiante en la base de datos
                updated = False
                new_entry = {
                    "studentName": student_name,
                    "studentEmail": student_email,
                    "team": team_name,
                    "paralelo": paralelo,
                    "text": new_text,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                for idx, entry in enumerate(topic_submissions):
                    if (entry.get("studentEmail", "").lower() == student_email and student_email) or \
                       (entry.get("studentName", "").lower() == student_name.lower()):
                        topic_submissions[idx] = new_entry
                        updated = True
                        break
                if not updated:
                    topic_submissions.append(new_entry)

                db[topic_id] = topic_submissions
                save_db(db)

                response = {
                    "allowed": True,
                    "similarity": max_sim,
                    "message": "Respuesta original verificada y registrada exitosamente en la base de datos de la cátedra."
                }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            return

        if self.path == "/api/team-chat":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            chat_file = os.path.join(DIRECTORY, "team_chat_db.json")
            chat_data = []
            if os.path.exists(chat_file):
                try:
                    with open(chat_file, "r", encoding="utf-8") as f:
                        chat_data = json.load(f)
                except Exception:
                    chat_data = []

            if "timestamp" not in data or not data["timestamp"]:
                data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if "id" not in data or not data["id"]:
                data["id"] = f"tc-{len(chat_data) + 1}"

            chat_data.append(data)

            # Si es una consulta al docente y se solicita respuesta automática de cátedra
            auto_reply = data.get("autoReplyDocente", False)
            teacher_reply = None
            if data.get("category") == "duda" and auto_reply:
                q_text = data.get("text", "").lower()
                sec = str(data.get("section", "2"))
                author = data.get("author", "Estudiante")

                if "costo" in q_text or "precio" in q_text or "financier" in q_text or "margen" in q_text or "equilibrio" in q_text:
                    resp_text = f"Estimado(a) {author} y equipo: Respecto a su consulta financiera, recuerden que de acuerdo a John Mullins (The New Business Road Test), todo análisis debe desglosar con precisión el Margen de Contribución Unitario (MCU = Precio - Costo Variable) para absorber los Costos Fijos operativos. Asegúrense de reflejar estos valores tanto en el Paso 11 del Proyecto como en la Diapositiva 8 del Pitch Deck."
                elif "legal" in q_text or "sas" in q_text or "ebc" in q_text or "senescyt" in q_text or "ley" in q_text:
                    resp_text = f"Estimado(a) {author}: La Ley Orgánica de Emprendimiento e Innovación faculta a los proyectos universitarios de la UG a formalizarse como SAS con capital simbólico y solicitar calificación RNE ante el Ministerio de Producción. Esto les otorga acceso preferente a fondos concursables y convenios de vinculación tecnológica con la FII. Citen los artículos pertinentes en el Paso 2."
                elif "canvas" in q_text or "osterwalder" in q_text or "valor" in q_text or "segmento" in q_text:
                    resp_text = f"Estimado(a) {author}: Al estructurar el Business Model Canvas (Osterwalder & Pigneur), es fundamental que exista coherencia directa entre los Segmentos de Clientes (bloque 7) y la Propuesta de Valor (bloque 4). No redacten una propuesta genérica; enfoquen la cuantificación del dolor validado en campo."
                elif "pitch" in q_text or "feria" in q_text or "inversion" in q_text or "jurado" in q_text:
                    resp_text = f"Estimado(a) {author}: Para la Feria de Emprendimiento FII, el jurado evaluará con rigor la regla de los primeros 15 segundos (el Gancho/Hook) y la demostración de tracción con clientes reales. Apóyense en la Ficha Técnica de su prototipo y los datos de validación en piscinas de Guayas."
                else:
                    resp_text = f"Estimado(a) {author} y equipo AgroTech: He revisado su inquietud sobre la Sección {sec}. Su consulta demuestra un avance metódico significativo. Cuiden que todo argumento esté respaldado en los datos recogidos en territorio y alineado con los Resultados de Aprendizaje del Sílabo. Queda registrada esta evidencia de interacción docente."

                teacher_reply = {
                    "id": f"tc-{len(chat_data) + 1}",
                    "author": "Econ. Janio Cerezo Piedrahita, Mgs.",
                    "email": "janio.cerezop@ug.edu.ec",
                    "role": "Docente Cátedra & Administrador",
                    "team": "Cátedra Emprendimiento e Innovación FII",
                    "paralelo": "Facultad de Ingeniería Industrial",
                    "category": "docente",
                    "categoryLabel": "Respuesta de Cátedra",
                    "section": sec,
                    "sectionTitle": data.get("sectionTitle", f"Sección {sec}"),
                    "text": resp_text,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "oficial",
                    "replyToId": data["id"]
                }
                chat_data.append(teacher_reply)
                data["status"] = "respondido"

            try:
                with open(chat_file, "w", encoding="utf-8") as f:
                    json.dump(chat_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print("Error al guardar chat:", e)

            response = {
                "success": True, 
                "savedMessage": data, 
                "teacherReply": teacher_reply,
                "totalMessages": len(chat_data)
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            return

        if self.path == "/api/project-step":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            proj_file = os.path.join(DIRECTORY, "projects_cloud_db.json")
            proj_data = {}
            if os.path.exists(proj_file):
                try:
                    with open(proj_file, "r", encoding="utf-8") as f:
                        proj_data = json.load(f)
                except Exception:
                    proj_data = {}

            team_key = data.get("teamName", "Equipo Sin Nombre")
            step_id = data.get("stepId", "p1")
            if team_key not in proj_data:
                proj_data[team_key] = {
                    "teamName": team_key,
                    "studentAuthor": data.get("studentAuthor", "Estudiante FII"),
                    "paralelo": data.get("paralelo", "IND-8-2"),
                    "steps": {},
                    "lastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

            proj_data[team_key]["steps"][step_id] = {
                "stepId": step_id,
                "stepNum": data.get("stepNum", ""),
                "title": data.get("title", ""),
                "payload": data.get("payload", {}),
                "author": data.get("studentAuthor", "Estudiante FII"),
                "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            proj_data[team_key]["lastUpdated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                with open(proj_file, "w", encoding="utf-8") as f:
                    json.dump(proj_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print("Error guardando proyecto en la nube:", e)

            response = {
                "success": True,
                "message": f"Artefacto {step_id} sincronizado exitosamente en la nube de la cátedra.",
                "totalTeamSteps": len(proj_data[team_key]["steps"])
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            return

        if self.path == "/api/zoom-attendance":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            zoom_file = os.path.join(DIRECTORY, "zoom_attendance_db.json")
            zoom_data = []
            if os.path.exists(zoom_file):
                try:
                    with open(zoom_file, "r", encoding="utf-8") as f:
                        zoom_data = json.load(f)
                except Exception:
                    zoom_data = []

            # Evitar duplicados por id o hash
            cert_id = data.get("id", f"zoom-{len(zoom_data) + 1}")
            data["id"] = cert_id
            if "savedAt" not in data:
                data["savedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Actualizar si ya existía ese certificado
            existing_idx = next((i for i, z in enumerate(zoom_data) if z.get("id") == cert_id), None)
            if existing_idx is not None:
                zoom_data[existing_idx] = data
            else:
                zoom_data.append(data)

            try:
                with open(zoom_file, "w", encoding="utf-8") as f:
                    json.dump(zoom_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print("Error guardando certificado Zoom:", e)

            response = {
                "success": True,
                "message": "Asistencia y notas en Zoom sincronizadas en la nube docente.",
                "totalCertificates": len(zoom_data)
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            return

        super().do_POST()

    def do_GET(self):
        if self.path.startswith("/api/team-chat"):
            chat_file = os.path.join(DIRECTORY, "team_chat_db.json")
            chat_data = []
            if os.path.exists(chat_file):
                try:
                    with open(chat_file, "r", encoding="utf-8") as f:
                        chat_data = json.load(f)
                except Exception:
                    chat_data = []
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(chat_data, ensure_ascii=False).encode('utf-8'))
            return

        if self.path == "/api/database-stats":
            db = load_db()
            total_answers = sum(len(subms) for subms in db.values())
            topics_with_answers = len([t for t, subms in db.items() if len(subms) > 0])
            stats = {
                "totalSubmissions": total_answers,
                "activeTopics": topics_with_answers,
                "docente": "Econ. Janio Cerezo Piedrahita, Mgs."
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(stats, ensure_ascii=False).encode('utf-8'))
            return

        if self.path == "/api/teacher-audit-log":
            audit_file = os.path.join(DIRECTORY, "antifraud_audit_log.json")
            audit_log = []
            if os.path.exists(audit_file):
                try:
                    with open(audit_file, "r", encoding="utf-8") as af:
                        audit_log = json.load(af)
                except Exception:
                    audit_log = []
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(audit_log, ensure_ascii=False).encode('utf-8'))
            return

        if self.path == "/api/all-submissions":
            db = load_db()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(db, ensure_ascii=False).encode('utf-8'))
            return

        if self.path == "/api/projects-data":
            proj_file = os.path.join(DIRECTORY, "projects_cloud_db.json")
            proj_data = {}
            if os.path.exists(proj_file):
                try:
                    with open(proj_file, "r", encoding="utf-8") as f:
                        proj_data = json.load(f)
                except Exception:
                    proj_data = {}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(proj_data, ensure_ascii=False).encode('utf-8'))
            return

        if self.path == "/api/zoom-attendance":
            zoom_file = os.path.join(DIRECTORY, "zoom_attendance_db.json")
            zoom_data = []
            if os.path.exists(zoom_file):
                try:
                    with open(zoom_file, "r", encoding="utf-8") as f:
                        zoom_data = json.load(f)
                except Exception:
                    zoom_data = []
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(zoom_data, ensure_ascii=False).encode('utf-8'))
            return

        super().do_GET()

def start_server():
    os.chdir(DIRECTORY)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), EIFIIServerHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print("=" * 65)
        print(" CAMPUS DOCENTE EI-FII · UNIVERSIDAD DE GUAYAQUIL")
        print(" Facultad de Ingeniería Industrial")
        print(" Cátedra: Emprendimiento e Innovación")
        print(" Docente & Administrador: Econ. Janio Cerezo Piedrahita, Mgs.")
        print(f" Servidor ejecutándose en: {url}")
        print(" Motor de Detección de Coincidencias y Plagio ACTIVO.")
        print("=" * 65)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")
            httpd.server_close()

if __name__ == "__main__":
    start_server()
