import sqlite3
import os
from dotenv import load_dotenv
from google import genai

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

def execute_sql(db_path, query):
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
        return column_names, results
    except Exception as e:
        return None, f"SQL Çalıştırma Hatası: {e}"
    finally:
        conn.close()

def main():
    if not os.path.exists(DB_FILE):
        print(f"Hata: {DB_FILE} bulunamadı.")
        return

    # Check API Key
    if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "your_gemini_api_key_here":
        print("Hata: Geçerli bir Gemini API anahtarı bulunamadı. Lütfen .env dosyasındaki GEMINI_API_KEY'i kendi anahtarınızla değiştirin.")
        return

    print("Veritabanı şeması okunuyor...")
    schema = get_database_schema(DB_FILE)

    gemini_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=gemini_key)
    
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
    {schema}
    """

    chat_session = client.chats.create(
        model='gemini-2.5-flash',
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.0
        )
    )

    print("\n--- Doğal Dilden SQL'e Uygulamasına Hoşgeldiniz ---")
    print("Örnek Sorular: 'En pahalı ürün hangisi?', 'Ahmet Yılmaz ne kadarlık sipariş vermiş?'")
    print("Çıkmak için 'q' veya 'exit' yazabilirsiniz.")

    while True:
        user_input = input("\nSoru: ")
        if user_input.lower() in ['q', 'exit', 'çıkış']:
            break

        if not user_input.strip():
            continue

        print("Cevap düşünülüyor (Gemini API)...")
        # 1. SQL Sorgusunu Üret
        sql_query = ask_llm_for_sql(chat_session, user_input)
        
        if not sql_query:
            continue
            
        print(f"\n[Generated SQL] >> {sql_query}\n")

        # 2. Güvenlik Kontrolü (Sadece SELECT Komutları)
        if any(keyword in sql_query.upper() for keyword in ['DROP', 'DELETE', 'UPDATE', 'INSERT']):
            print("Uyarı: Uygulama güvenliği için sadece 'SELECT' (Okuma) sorgularına izin verilmektedir.")
            continue

        # 3. Üretilen SQL'i Veritabanında Çalıştır
        columns, results = execute_sql(DB_FILE, sql_query)

        if columns is None:
            print("Hata: Sorgu çalıştırılamadı:")
            print(results)
            continue
        
        # 4. Sonucu Düzenli Bir Şekilde Ekrana Bas
        if len(results) == 0:
            print("Sonuç: Hiçbir veri bulunamadı.")
        else:
            print("--- Bulunan Sonuçlar ---")
            print(" | ".join(columns))
            print("-" * 50)
            for row in results:
                print(" | ".join(map(str, row)))

if __name__ == "__main__":
    main()