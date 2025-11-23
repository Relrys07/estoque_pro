# apiEstouque

Pequena aplicação de controle de estoque construída com Streamlit e SQLite.

Conteúdo do repositório
- `estoque_pro.py` — app Streamlit principal
- `estoque_pro.db` — banco SQLite (gerado em execução)

Dependências
- streamlit
- pandas
- earthengine-api

Como rodar localmente (PowerShell):

```powershell
Set-Location 'c:\Users\relry\Desktop\estouque_pro'
C:/Users/relry/AppData/Local/Microsoft/WindowsApps/python3.13.exe -m pip install -r requirements.txt
C:/Users/relry/AppData/Local/Microsoft/WindowsApps/python3.13.exe -m streamlit run appEstoque.py
```

Publicar no GitHub (passos rápidos)

1. Crie um repositório no GitHub usando este link (já preencheu o nome `estoque_pro.py`):

https://github.com/new?name=estoque_pro

2. No seu computador, no diretório do projeto, rode:

```powershell
cd 'c:\Users\relry\Desktop\estoque_pro'
git init
git add .
git commit -m "Initial commit - estoque_pro"
# Substitua <USERNAME> e <REPO> pelo seu usuário e nome do repositório
git remote add origin https://github.com/<USERNAME>/estoque_pro.git
git branch -M main
git push -u origin main
```

Observações
- Se o repositório for privado, você pode usar SSH em vez do https.
- Se preferir, eu posso gerar um `.zip` do projeto ou dar instruções para criar automaticamente o repositório via GitHub CLI (`gh`).

Se quiser, eu também posso: gerar um `README` em inglês, adicionar um `LICENSE`, ou criar um `workflow` GitHub Actions para testes/format.
