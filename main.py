import sqlite3
import os
from dotenv import load_dotenv  # type: ignore
from google import genai  # type: ignore
from flask import Flask, request, jsonify, render_template_string  # type: ignore
from flask_cors import CORS  # type: ignore

# Load environment variables
load_dotenv()

DB_FILE = "Chinook_Sqlite.sqlite"

def get_database_schema(db_path):
    """Retrieve the CREATE TABLE statements for all tables in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence';")
    tables = cursor.fetchall()
    conn.close()
    
    schema = ""
    for table_name, table_sql in tables:
        schema += f"{table_sql}\n"
    return schema

def ask_llm_for_sql(chat_session, user_prompt):
    """Asks Gemini to generate a SQL query using conversational memory."""
    try:
        response = chat_session.send_message(user_prompt)
        sql_query = response.text.strip()
        
        # Extra safety fallback in case LLM still uses markdown block
        if sql_query.startswith("```sql"):
            sql_query = sql_query[6:]
        if sql_query.startswith("```"):
            sql_query = sql_query[3:]
        if sql_query.endswith("```"):
            sql_query = sql_query[:-3]
            
        return sql_query.strip()
    except Exception as e:
        print(f"LLM API Hatası: {e}")
        return None

def execute_sql(db_path, query) -> tuple:
    """Executes the given SQL query and returns the column headers and row results."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        # Some queries like DROP don't have description if they execute without fetching.
        if cursor.description:
            column_names = [description[0] for description in cursor.description]
        else:
            column_names = ["Kayıt Etkilenenler"]
            results = [[cursor.rowcount]]
        ret = (column_names, results)
    except Exception as e:
        ret = (None, f"SQL Çalıştırma Hatası: {e}")
    finally:
        conn.close()
    return ret

app = Flask(__name__)
CORS(app)

schema = None

def get_schema():
    global schema
    if schema is None:
        schema = get_database_schema(DB_FILE)
        if schema is None:
            schema = ""
    return schema

def create_chat_session():
    gemini_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=gemini_key)
    
    db_schema = get_schema()
    
    system_prompt = f"""
    Sen bir SQL uzmanısın. Görevin, kullanıcının girdiği Türkçe doğal dil sorusunu 
    aşağıdaki veritabanı şemasına (SQLite) uygun ve kesin doğru bir arama SQL (SELECT) sorgusuna çevirmektir.

    İPUÇLARI VE KURALLAR:
    1. Metin aramalarında Türkçe karakter ve büyük/küçük harf farklılıklarından kaçınmak için LIKE operatörü kullan (Örn: isim LIKE '%Ahmet%').
    2. "Kimin", "Kim", "Hangi Müşteri" diyorsa `users` tablosunu `orders` ile birleştir (JOIN yap).
    3. "En pahalı", "En ucuz", "En fazla" gibi durumlarda `ORDER BY` ve `LIMIT 1` kullan.
    4. "Kaç tane" gibi kelimeler geçiyorsa `COUNT()` fonksiyonunu kullan.
    5. Cevap olarak ASLA markdown sembolleri (```sql veya ```) kullanma! Yalnızca saf SQL metnini gönder.
    6. ASLA açıklama parantezi veya fazladan bilgi yazma. Sadece çalışan bir SQL kodu ver.
    7. ÖNEMLİ: Sen bir sohbet arayüzüsün. Kullanıcı "Peki onun fiyatı ne?", "O ürünü kim almış" gibi geçmişten bahseden sorular soruyorsa, ÖNCEKİ MESAJLARA BAKARAK eski bağlam üzerinden yeni bir SQL yaz. Örneğin "fiyatı 5000 altı ürün kaç tane" diye sorup sonra "peki o ürünler ne" derse yeni SQL sorgu "SELECT * FROM products WHERE price < 5000" olmalıdır.

    İşte Veritabanı Şeması:
    {db_schema}
    """

    return client.chats.create(
        model='gemini-2.5-flash',
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.0
        )
    )

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json or {}
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'Lütfen bir soru yazın.'}), 400
    
    try:
        # Create client and chat session directly in this scope
        gemini_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=gemini_key)
        
        db_schema = get_schema()
        
        system_prompt = f"""
        Sen bir SQL uzmanısın. Görevin, kullanıcının girdiği Türkçe doğal dil sorusunu 
        aşağıdaki veritabanı şemasına (SQLite) uygun ve kesin doğru bir arama SQL (SELECT) sorgusuna çevirmektir.

        İPUÇLARI VE KURALLAR:
        1. Metin aramalarında Türkçe karakter ve büyük/küçük harf farklılıklarından kaçınmak için LIKE operatörü kullan.
        2. Cevap olarak ASLA markdown sembolleri (```sql veya ```) kullanma! Yalnızca saf SQL metnini gönder.
        3. ASLA açıklama yazma. Sadece çalışan bir SQL kodu ver.

        İşte Veritabanı Şeması:
        {db_schema}
        """

        chat_session = client.chats.create(
            model='gemini-2.5-flash',
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.0
            )
        )
        
        # Get response
        response = chat_session.send_message(question)
        sql_query = response.text.strip()
        
        # Clean markdown
        if sql_query.startswith("```sql"):
            sql_query = sql_query[6:]
        if sql_query.startswith("```"):
            sql_query = sql_query[3:]
        if sql_query.endswith("```"):
            sql_query = sql_query[:-3]
        sql_query = sql_query.strip()
        
        if not sql_query:
            return jsonify({'error': 'SQL üretilemedi.'}), 500
        
        # Security check
        if any(keyword in sql_query.upper() for keyword in ['DROP', 'DELETE', 'UPDATE', 'INSERT']):
            return jsonify({'error': 'Güvenlik: Sadece SELECT sorgularına izin veriliyor.'}), 400
        
        # Execute SQL
        columns, results = execute_sql(DB_FILE, sql_query)
        
        if columns is None:
            return jsonify({'error': f'SQL hatası: {results}'}), 500
        
        return jsonify({
            'sql': sql_query,
            'columns': columns,
            'results': results,
            'row_count': len(results)
        })
        
    except Exception as e:
        print(f"Hata: {e}")
        return jsonify({'error': f'SQL üretilemedi: {str(e)}'}), 500

@app.route('/')
def serve_html():
    with open('text_to_sql.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/styles.css')
def serve_css():
    with open('styles.css', 'r', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'text/css'}

@app.route('/script.js')
def serve_js():
    with open('script.js', 'r', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'application/javascript'}

if __name__ == "__main__":
    app.run(debug=False, port=5001)