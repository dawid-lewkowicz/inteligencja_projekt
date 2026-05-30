import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("Błąd: Brak klucza w pliku .env!")

class SyllabusChatbot:
    def __init__(self, database_path="knowledge_base.json"):
        # temperature=0 powoduje brak halucynacji
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.database = self._load_database(database_path)
        self.course_names = [course["nazwa"] for course in self.database]
        self.chat_history = []

    def _load_database(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _identify_course(self, user_query: str) -> str:
        history_str = ""
        for msg in self.chat_history: 
            history_str += f"{msg['role']}: {msg['content']}\n"

        system_prompt = (
            "Jesteś zaawansowanym systemem kategoryzacji zapytań (Routerem) dla asystenta Dziekanatu.\n"
            "Twoim zadaniem jest ekstrakcja intencji użytkownika i dopasowanie jej do bazy wiedzy.\n\n"
            f"Dostępna baza przedmiotów: {', '.join(self.course_names)}\n\n"
            "ZASADY KATEGORYZACJI:\n"
            "- Zwróć DOKŁADNĄ NAZWĘ PRZEDMIOTU z bazy, jeśli zapytanie dotyczy konkretnego kursu.\n"
            "- UWAGA NA ZAIMKI: Jeśli użytkownik używa słów typu 'ten przedmiot', 'kto to prowadzi', "
            "MUSISZ sprawdzić w Historii Konwersacji, o jakim przedmiocie była mowa i zwrócić jego nazwę.\n"
            "- Zwróć 'GLOBALNE', jeśli zapytanie wymaga przeanalizowania całej bazy (np. pytania o statystyki, porównania, kto prowadzi najwięcej zajęć, podsumowania ECTS czy ogólną listę przedmiotów).\n"
            "- Zwróć 'WIELE', jeśli zapytanie jest zbyt ogólne i pasuje do więcej niż jednego przedmiotu (np. 'programowanie').\n"
            "- Zwróć 'BRAK', jeśli zapytanie to luźna konwersacja (np. przywitanie) lub temat niezwiązany ze studiami.\n\n"
            "FORMAT WYJŚCIOWY:\n"
            "Masz zakaz używania jakichkolwiek innych słów. Zwróć wyłącznie jeden z powyższych identyfikatorów."
        )
        
        user_prompt = (
            "Historia Konwersacji:\n"
            "<historia>\n"
            "{history}\n"
            "</historia>\n\n"
            "Najnowsze zapytanie użytkownika: {query}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])
        
        chain = prompt | self.llm    
        response = chain.invoke({"history": history_str, "query": user_query})
        
        return response.content.strip()

    def ask(self, user_query: str) -> str:
        raw_match = self._identify_course(user_query).strip().replace(".", "")
        matched_course = raw_match.upper() if raw_match.upper() in ["WIELE", "GLOBALNE", "BRAK"] else raw_match
        
        print(f"\n[DEBUG ROUTERA] Zidentyfikowano jako: {matched_course}")
        
        if matched_course == "WIELE":
            context_str = f"[ZAPYTANIE NIEJEDNOZNACZNE]. Lista dostępnych przedmiotów w bazie: {', '.join(self.course_names)}."
            
        elif matched_course == "GLOBALNE":
            context_str = json.dumps(self.database, indent=2, ensure_ascii=False)
            
        elif matched_course == "BRAK":
            context_str = "[BRAK DANYCH W BAZIE / LUŹNA ROZMOWA]. Poinformuj studenta, że pomagasz tylko w kwestiach sylabusów."
            
        else:
            context = None
            normalized_matched = matched_course.lower().replace(".", "")
            
            for course in self.database:
                db_name = course["nazwa"].strip().lower().replace(".", "")
                
                if normalized_matched and (normalized_matched in db_name or db_name in normalized_matched):
                    context = course
                    break
            
            if not context:
                context_str = "[NIE ZNALEZIONO PRZEDMIOTU W BAZIE]."
            else:
                context_str = json.dumps(context, indent=2, ensure_ascii=False)

        system_chat_prompt = (
            "Jesteś oficjalnym Wirtualnym Asystentem Wydziału Informatyki Uniwersytetu Gdańskiego.\n"
            "Twoim zadaniem jest odpowiadanie na pytania studentów wyłącznie na podstawie dostarczonych danych z sylabusów.\n\n"
            
            "INSTRUKCJE ZACHOWANIA:\n"
            "1. Ścisłe trzymanie się faktów: Odpowiadaj TYLKO na podstawie informacji zawartych w tagach <sylabus>. Jeśli odpowiedzi tam nie ma, poinformuj o tym wyraźnie. Nie zmyślaj.\n"
            "2. Zapytania globalne: Jeśli w tagu <sylabus> otrzymasz dużą listę przedmiotów (JSON), przeanalizuj ją w całości, aby precyzyjnie odpowiedzieć na przekrojowe pytanie studenta (np. o listę prowadzących, sumę punktów ECTS, itp.).\n"
            "3. Niejednoznaczność (WIELE): Jeśli w tagu <sylabus> otrzymasz informację [ZAPYTANIE NIEJEDNOZNACZNE], przeanalizuj zapytanie użytkownika, znajdź na dostarczonej liście te przedmioty, które mogą do niego pasować, i poproś o doprecyzowanie, wymieniając je.\n"
            "4. Luźna rozmowa (BRAK): Jeśli w tagu <sylabus> otrzymasz informację [BRAK DANYCH...], kulturalnie nakieruj rozmowę z powrotem na temat studiów.\n"
            "5. Ochrona edukacyjna (Tarcza): Jesteś asystentem administracyjnym. Jeśli student prosi o napisanie kodu lub rozwiązanie zadania, grzecznie odmów.\n"
            "6. Formatowanie: Używaj ikon 📚 (podstawowa/uzupełniająca) oraz 🌐 (e-zasoby) przy literaturze. Używaj wypunktowań dla czytelności.\n\n"
            
            "DANE REFERENCYJNE:\n"
            "<sylabus>\n"
            "{context}\n"
            "</sylabus>"
        )

        history_str = ""
        for msg in self.chat_history: 
            history_str += f"{msg['role']}: {msg['content']}\n"

        user_prompt = (
            "Historia Konwersacji:\n"
            "<historia>\n"
            "{history}\n"
            "</historia>\n\n"
            "Najnowsze zapytanie użytkownika: {query}"
        )

        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", system_chat_prompt),
            ("user", user_prompt)
        ])

        conversation_chain = chat_prompt | self.llm
        
        answer = conversation_chain.invoke({
            "context": context_str, 
            "history": history_str, 
            "query": user_query
        })
        
        output_text = answer.content

        self._update_memory(user_query, output_text)
        return output_text

    def _update_memory(self, user_query: str, output_text: str):
        self.chat_history.append({"role": "Student", "content": user_query})
        self.chat_history.append({"role": "AI", "content": output_text})
        if len(self.chat_history) > 6:
            self.chat_history = self.chat_history[-6:]

if __name__ == "__main__":
    print("Inicjalizacja Inteligentnego Asystenta Sylabusów...")
    try: # try na wypadek błędu połączenia z OpenAI API
        bot = SyllabusChatbot("knowledge_base.json")
        print("Bot gotowy do rozmowy! Wpisz 'exit' aby wyjść.\n")
        
        while True:
            pytanie = input("Student: ")
            if pytanie.lower() == 'exit':
                print("Do widzenia!")
                break
                
            if not pytanie.strip():
                continue
            
            try: # gdy będzie problem z połącznieme w trakcie rozmowy    
                odpowiedz = bot.ask(pytanie)
                print(f"\nAI:\n{odpowiedz}\n")
            except Exception as api_err:
                print(f"\n[SYSTEM] Problem z serwerem API (Sprawdź internet): {api_err}\n")
                
            print("-" * 40)
            
    except Exception as e:
        print(f"\n[BŁĄD KRYTYCZNY STARTU] Nie udało się zainicjalizować bota. Powód: {e}")