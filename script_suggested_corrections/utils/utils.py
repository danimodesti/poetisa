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
            # Remove qualquer espaço extra ou caracteres de controle como \n e \r
            palavra = linha.strip().split(',')[0].strip()  # Pega a palavra antes da vírgula e remove espaços
            # Adiciona apenas se contiver caracteres especiais/acento, que é a 'corrupção' que queremos corrigir
            if regex_caracteres_especiais.search(palavra):
                palavras.add(palavra)
    return palavras