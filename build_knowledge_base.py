import pdfplumber
import re
import json
from models import SyllabusModel, EfektUczenia, Ocenianie
from pathlib import Path

def extract_syllabus_data(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    if len(text.strip()) < 100:
        print(f"OSTRZEŻENIE: Plik {file_path} wydaje się być skanem lub jest pusty. Pomijam.")
        return None

    data = SyllabusModel()

    def extract(pattern, string, group=1):
        match = re.search(pattern, string)
        return match.group(group).strip() if match else ""

# tekst = "Liczba punktów ECTS wynosi 7.0 i ani jednego więcej."

# # Szukamy słowa "wynosi", spacji, a potem ŁAPIEMY W NAWIASY liczbę.
# wzorzec = r"wynosi\s+(.*?)\s+i"

# match = re.search(wzorzec, tekst)

# # Sprawdzamy, co kryje się pod konkretnymi numerami grup:
# print(match.group(0))  # Wynik: "wynosi 7.0 i"
# print(match.group(1))  # Wynik: "7.0"

    ########################################################################################
    #                   W wersji produkcyjnej prędziej użyje się LLM Parsing niż Regex'ów
    ########################################################################################

    # podstawowe informacje
    data.nazwa = extract(r'Nazwa i kod przedmiotu\s+(.*?)(?:,|$)', text)
    data.kod = extract(r'PG_\d+', text, 0)
    data.kierunek = extract(r'Kierunek studiów\s+(.*?)\n', text)
    data.ects = extract(r'Liczba punktów ECTS\s+(\d+\.?\d*)', text)
    data.forma_zaliczenia = extract(r'Forma zaliczenia\s+(.*?)\n', text)

    # wykładowcy
    data.odpowiedzialny = extract(r'Odpowiedzialny za przedmiot\s+(.*?)\n', text).strip()

    wykladowcy_block = extract(r'Prowadzący zajęcia z przedmiotu\s+(.*?)(?=Formy zajęć)', text.replace('\n', ' ### '))
                                    # wrzucamu ### zamiast znaku nowej linii i potem pozwala nam do na łatwe wypisanie wykładowców
    if wykladowcy_block:
        names = re.findall(r'(?:dr|mgr|prof\.)[^\#]+', wykladowcy_block)
        for n in names:
            clean_name = n.strip()
            if clean_name not in data.prowadzacy and len(clean_name) > 3:
                data.prowadzacy.append(clean_name)

    # godziny zajęć
    godziny_match = re.search(r'Liczba godzin zajęć\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)', text)
    if godziny_match:
        data.godziny = {
            "wyklad": godziny_match.group(1) + "h",
            "cwiczenia": godziny_match.group(2) + "h",
            "laboratorium": godziny_match.group(3) + "h",
            "projekt": godziny_match.group(4) + "h",
            "seminarium": godziny_match.group(5) + "h"
        }

    # aktywność studenta
    aktywnosc_match = re.search(r'Liczba godzin pracy[^\d]*(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)', text)
    if aktywnosc_match:
        data.aktywnosc_studenta = {
            "zajecia_dydaktyczne": aktywnosc_match.group(1) + "h",
            "konsultacje": aktywnosc_match.group(2) + "h",
            "praca_wlasna": aktywnosc_match.group(3) + "h",
            "razem": aktywnosc_match.group(4) + "h"
        }

    # cel i program                             positive lookahead
    cel_block = extract(r'Cel przedmiotu(.*?)(?=Data wygenerowania|Efekty)', text.replace('\n', ' '))
    if cel_block:                               
        data.cel = cel_block.replace("Celem przedmiotu jest", "").strip()

    program_block = extract(r'Treści przedmiotu(.*?)Wymagania wstępne', text.replace('\n', ' '))
    for bullet in program_block.split('•'):
        clean_b = bullet.strip()
        if len(clean_b) > 5: data.program.append(clean_b)

    # ocenianie
    ocenianie_block = extract(r'Sposób oceniania \(składowe\)(.*?)(?=Zalecana lista lektur|Adresy eZasobów|Praktyki)', text.replace('\n', ' '))
    if ocenianie_block:
                                    # dowolny tekst po którym występują dwa znaki %
        skladniki = re.findall(r'([a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ0-9\s\-\.]+?)\s+(\d+\.?\d*%)\s+(\d+\.?\d*%)', ocenianie_block)
        for nazwa, prog, waga in skladniki:
            clean_nazwa = nazwa.replace("Składowa oceny końcowej", "").replace("Próg zaliczeniowy", "").strip()
            if len(clean_nazwa) > 2:
                data.ocenianie.append(Ocenianie(typ=clean_nazwa.lower(), prog=prog, waga=waga))

    # literatura
    zasoby_block = extract(r'Adresy eZasobów(.*?)(?=Przykładowe zagadnienia|Praktyki)', text.replace('\n', ' '))
    data.ezasoby = re.findall(r'(https?://[^\s]+)', zasoby_block)

    lit_block = extract(r'Podstawowa lista lektur(.*?)Adresy eZasobów', text.replace('\n', ' '))
    if lit_block:
        parts = re.split(r'Uzupełniająca lista lektur', lit_block)
        
        def extract_books(raw_text):
            # jeśli są ISBN to tniemy według nich
            if "ISBN" in raw_text:
                fragments = re.split(r'(ISBN:\s*[\d\-X]+)', raw_text)
                books = []
                for i in range(0, len(fragments) - 1, 2):
                    book = fragments[i].strip() + " " + fragments[i+1].strip()
                    book = book.replace('Python.', 'Python. ')
                    if len(book) > 10: books.append(book.strip())
                if len(fragments) % 2 != 0 and len(fragments[-1].strip()) > 10:
                    books.append(fragments[-1].strip())
                return books
            else:
                # jeśli nie ma, tniemy po punktorach (•) lub liczbach z kropką (1. 2.)
                books = re.split(r'•|\d+\.', raw_text)
                return [b.strip() for b in books if len(b.strip()) > 10]

        data.literatura.podstawowa = extract_books(parts[0])
        if len(parts) > 1:
            data.literatura.uzupelniajaca = extract_books(parts[1])
    
    # praktyki
    praktyki_str = extract(r'Praktyki zawodowe(.*?)(?=\nData wygenerowania|\Z)', text.replace('\n', ' '))
    if "Nie dotyczy" not in praktyki_str and praktyki_str:
        data.praktyki = praktyki_str.replace("w ramach przedmiotu", "").strip()

    # efekty uczenia
    with pdfplumber.open(file_path) as pdf_table:
        for page in pdf_table.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    cells = [str(c).strip() if c else "" for c in row]
                    
                    # szukamy [INFL3_
                    for i, c in enumerate(cells):
                        if "[INFL3_" in c and i + 2 < len(cells):
                            # jeśli znaleźliśmy, bierzemy tę komórkę i dwie kolejne
                            data.efekty_uczenia.append(EfektUczenia(
                                efekt_kierunkowy=cells[i].replace('\n', ' ').strip(),
                                efekt_z_przedmiotu=cells[i+1].replace('\n', ' ').strip(),
                                sposob_weryfikacji=cells[i+2].replace('\n', ' ').strip()
                            ))
                            break # znaleźliśmy efekt, kończymy przeszukiwać ten wiersz

    return data

def build_knowledge_base(folder_name="pdfs", output_file="knowledge_base.json"):
    folder_pdfs = Path(folder_name)
    
    if not folder_pdfs.exists() or not folder_pdfs.is_dir():
        print(f"Błąd: Folder '{folder_name}' nie istnieje w tym katalogu!")
        return

    pdf_files = list(folder_pdfs.glob("*.pdf"))
    
    if not pdf_files:
        print(f"Błąd: Folder '{folder_name}' nie zawiera plików PDF.")
        return

    print(f"Znaleziono {len(pdf_files)} sylabusów. Rozpoczynam maszynową ekstrakcję...")
    
    knowledge_base = []

    for path_to_pdf in pdf_files:
        print(f"Przetwarzam: {path_to_pdf.name}...", end=" ")
        
        try:
            syllabus_obj = extract_syllabus_data(str(path_to_pdf))
            
            knowledge_base.append(syllabus_obj.model_dump())
            print("SUKCES")
            
        except Exception as e:
            print(f"BŁĄD! (Zignorowano plik). Powód: {e}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, indent=4, ensure_ascii=False)

    print("-" * 50)
    print(f"Zakończono! Pomyślnie wyodrębniono {len(knowledge_base)}/{len(pdf_files)} sylabusów.")
    print(f"Twoja baza wiedzy jest gotowa w pliku: {output_file}")

if __name__ == "__main__":
    build_knowledge_base("pdfs", "knowledge_base.json")