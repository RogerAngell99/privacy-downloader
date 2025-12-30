import os
import sys

def reset_database():
    db_path = 'metadata.db'
    if os.path.exists(db_path):
        print(f"⚠️  Atenção: Isso apagará o banco de dados '{db_path}'.")
        print("   Isso forçará o scraper a verificar e baixar TODOS os arquivos novamente para o novo diretório.")
        confirm = input("Tem certeza que deseja continuar? (s/n): ").strip().lower()
        
        if confirm in ['s', 'sim', 'y', 'yes']:
            try:
                os.remove(db_path)
                print("✅ Banco de dados apagado com sucesso.")
                print("Agora execute 'python main.py' para baixar os arquivos no novo local.")
            except Exception as e:
                print(f"❌ Erro ao apagar banco de dados: {e}")
        else:
            print("Operação cancelada.")
    else:
        print(f"Arquivo '{db_path}' não encontrado. Nada a fazer.")

if __name__ == "__main__":
    reset_database()
