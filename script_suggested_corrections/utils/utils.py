import re # Procurar padrões com expressões regulares

# Caracteres possíveis para correções
caracteres_especiais = "áàâãäçéèêëíìîïóòôõöúùûüñ"

"""
    Função que abre o arquivo de léxico de suporte e retorna um 'dicionário' para consultar apenas as
    palavras com caracteres especiais.
"""
def carregar_lexico(caminho_lexico):
    # Define um padrão de expressão regular para verificar caracteres especiais/acentos
    regex_caracteres_especiais = re.compile(f'[{caracteres_especiais}]', re.IGNORECASE)
    
    palavras = set() # Sem duplicatas
    with open(caminho_lexico, 'r', encoding='utf-8') as f:
        for linha in f:
            if linha.strip(): 
                palavra = linha.split('\t')[0]  # Pega a primeira coluna
                # Adiciona apenas se contiver caracteres especiais/acento, que é a 'corrupção' que queremos corrigir
                if regex_caracteres_especiais.search(palavra):
                    palavras.add(palavra)
    return palavras