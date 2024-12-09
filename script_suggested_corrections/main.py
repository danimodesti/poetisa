import re # Procurar padrões com expressões regulares
from bs4 import BeautifulSoup # Limpar HTML e deixar apenas texto visível
import os # Processar os arquivos e diretórios

### Variáveis globais para controlar caminhos de arquivos e constantes ###

# Léxico de suporte (lista possibilidades para substituição das palavras)
caminho_lexico = 'portilexicon-ud.tsv'  

# Caracteres possíveis para correções
caracteres_especiais = "áàâãäçéèêëíìîïóòôõöúùûüñ"

# Diretório dos arquivos originais a corrigir
diretorio_arqs_originais = 'Verbo-Brasil_html/'

#######################################################################################################

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

"""
    Função para abrir e retornar em uma variável o conteúdo do arquivo que precisa de substituições
    nas palavras, removendo o HTML 'técnico' e deixando apenas o texto plano visível.
"""
def obter_conteudo_arquivo_corrompido(caminho_arq_corrompido):
    with open(caminho_arq_corrompido, 'r', encoding='utf-8') as f:
        conteudo_arq_bruto = f.read()
    
    # Limpar o HTML
    soup = BeautifulSoup(conteudo_arq_bruto, 'html.parser')
    conteudo_arq_limpo = soup.get_text()  # Remove todas as tags HTML e deixa só o texto

    return conteudo_arq_limpo

"""
    Função que recebe o conteúdo do arquivo e retorna estrutura de dicionário com as palavras que 
    estão corrompidas e precisam de uma substituição, junto de suas linhas numeradas de aparição, 
    seus contextos (para ajudar a identificar o contexto e qual deve ser a palavra original) e um 
    campo para as substituições possíveis.
"""
def encontrar_palavras_corrompidas_e_contextos(conteudo_arq):
    # Divida o conteúdo do arquivo por linhas
    linhas = conteudo_arq.splitlines()

    # Dicionário (palavra_corrompida, nro_linha, contexto, substituições possíveis)
    palavras_corrompidas_dict = []

    # Entendendo a regex utilizada a seguir:
    # r -> para tratar como raw string, evitando slashs duplos em caracterees especiais, evitar escrever 
    #      \\b em vez de \b
    #
    # \w* -> capturar zero ou mais letras, números ou underscore (caracteres alfanuméricos).
    # Precisa usar * para permitir que a palavra comece com ?
    #
    # \?+ -> capturar um ou mais interrogações

    # Para capturar o 'contexto' --> Percorre cada linha com seu número
    for numero_linha, linha in enumerate(linhas, start=1):
        # Procura palavras corrompidas na linha
        corrompidas = re.findall(r"\w*\?+\w*", linha)

        for palavra in corrompidas:
            palavras_corrompidas_dict.append({
                "palavra": palavra,
                "linha": numero_linha,
                "contexto_original": linha.strip(),
                "substituicoes": []
            })

    return palavras_corrompidas_dict

"""
    Tentativa de substituição mais simples, apenas buscando as palavras exatas no léxico de apoio,
    alterando o dicionário ao adicionar as substituições encontradas.
"""
def pesquisar_no_lexico(palavra_dict, lexico):
    # Criando a regex dinâmica para a palavra corrompida
    regex_pattern = re.sub(r'\?', f'[{caracteres_especiais}]', palavra_dict["palavra"])

    # Encontrando todas as correspondências no léxico
    # IGNORECASE para dar match em palavras com letras maiúsculas
    palavra_dict["substituicoes"] = {
        palavra for palavra in lexico
        if re.fullmatch(regex_pattern, palavra, re.IGNORECASE)
    }

    # Resolver palavra com primeira letra maiúscula (casos raros e poucas possibilidades esperadas)
    if palavra_dict["palavra"][0].isupper():
        palavra_dict["substituicoes"] = {possibilidade.capitalize() for possibilidade in palavra_dict["substituicoes"]}

"""
    Verificar se palavra corrompida é um país e, por isso, dificilmente estará no léxico de suporte,
    apesar de ser palavra de uso comum.
"""
def pesquisar_paises(palavra_dict):
    # Criando a regex dinâmica para a palavra corrompida
    regex_pattern = re.sub(r'\?', f'[{caracteres_especiais}]', palavra_dict["palavra"])

    # Inicia um set para armazenar as substituições encontradas
    paises_encontrados = set()

    # Abre o arquivo com os nomes dos países
    with open('nomes_de_paises.txt', 'r', encoding='utf-8') as f:
        for linha in f:
            pais = linha.strip()  # Remove espaços em branco no início e fim da linha
            if re.fullmatch(regex_pattern, pais):
                paises_encontrados.add(pais)

    # Atualiza a lista de substituições com os países encontrados
    palavra_dict["substituicoes"].update(paises_encontrados)

"""
    Verificar se palavra corrompida é um nome próprio comum e, por isso, dificilmente estará no léxico de suporte.
"""
def pesquisar_pessoas(palavra_dict):
    # Criando a regex dinâmica para a palavra corrompida
    regex_pattern = re.sub(r'\?', f'[{caracteres_especiais}]', palavra_dict["palavra"])

    # Inicia um set para armazenar as substituições encontradas
    nomes_pessoas_encontrados = set()

    # Abre o arquivo com os nomes dos países
    with open('nomes_de_pessoas.txt', 'r', encoding='utf-8') as f:
        for linha in f:
            pais = linha.strip()  # Remove espaços em branco no início e fim da linha
            if re.fullmatch(regex_pattern, pais):
                nomes_pessoas_encontrados.add(pais)

    # Atualiza a lista de substituições com os países encontrados
    palavra_dict["substituicoes"].update(nomes_pessoas_encontrados)

"""
    Função que tenta identificar correções automáticas para as palavras que estão 'corrompidas', 
    decidindo em qual caso básico elas se encaixam: se busca no léxico, se aproxima de alguma palavra,
    mas não exatamente, se são apenas caracteres especiais indistinguíveis apenas pelo código...
"""
def procurar_substituicoes_palavras_corrompidas(palavras_corrompidas_dict, lexico):
    for palavra_corrompida in palavras_corrompidas_dict:
        if palavra_corrompida["palavra"] == '?': 
            palavra_corrompida["substituicoes"].extend(['?', '\'', '\"', 'é', 'à', 'ó', 'á'])
            continue
        elif palavra_corrompida["palavra"] == '??':
            palavra_corrompida["substituicoes"].extend('à')
            continue

        pesquisar_no_lexico(palavra_corrompida, lexico)

        qtd_possibilidades = len(palavra_corrompida["substituicoes"])
        if qtd_possibilidades == 0:  # nome de país ou nome de pessoa famosa?
            pesquisar_paises(palavra_corrompida)
        if qtd_possibilidades == 0:
            pesquisar_pessoas(palavra_corrompida)

"""
    Retorna a exibição em string da estrutura da palavra para os logs.
"""
def estrutura_palavra_log(palavra_corrompida):
    string = ""
    string += f'\tPalavra: {palavra_corrompida["palavra"]}\n'
    string += f'\tNúmero da linha no arquivo: {palavra_corrompida["linha"]}\n'
    string += f'\tContexto/frase original: \"{palavra_corrompida["contexto_original"]}\"\n'
    string += f'\tSubstituição(ões) encontrada(s): '

    return string

"""
    Os três logs pedidos são escritos para os casos processados, contendo, para cada um deles,
    o nome do arquivo, a frase original, a palavra corrompida e a correção sugerida/possível (se houver),
    separando os casos da seguinte forma:
    - inclui no log_sem_correcoes.txt se não foi possível distinguir uma correção;
    - inclui no log_uma_correcao.txt se foi possível encontrar exatamente uma correção;
    - inclui no log_n_correcoes.txt se foram encontradas múltiplas correções possíveis.
"""
def escrever_logs(logs, palavras_corrompidas_dict):
    for palavra_corrompida in palavras_corrompidas_dict:
        estrutura_palavra_log(palavra_corrompida)
        qtd_subst_encontradas = len(palavra_corrompida["substituicoes"])            

        if qtd_subst_encontradas == 0:
            logs[0].write(estrutura_palavra_log(palavra_corrompida) + "-\n")
            logs[0].write("--------------------------------------------------------\n")
        elif qtd_subst_encontradas == 1:
            logs[1].write(estrutura_palavra_log(palavra_corrompida) + str(palavra_corrompida["substituicoes"]) + "\n")
            logs[1].write("--------------------------------------------------------\n")
        else:
            logs[2].write(estrutura_palavra_log(palavra_corrompida) + str(palavra_corrompida["substituicoes"]) + "\n")
            logs[2].write("--------------------------------------------------------\n")

"""
    Função para prints adicionais.
"""
def exibir_info_na_tela(palavras_corrompidas_dict):
    for palavra_corrompida in palavras_corrompidas_dict:
            print(palavra_corrompida["palavra"], end=" | ")

####################################################################################################

def main():
    lexico = carregar_lexico(caminho_lexico)

    # Abrir os arquivos de log para escrita simultânea
    with open('log_sem_correcoes.txt', 'w', encoding='utf-8') as log1, \
        open('log_uma_correcao.txt', 'w', encoding='utf-8') as log2, \
        open('log_n_correcoes.txt', 'w', encoding='utf-8') as log3:

        logs = [log1, log2, log3]  # Lista de arquivos de log para passar às funções

        # Obter e ordenar os arquivos na pasta de forma alfabética
        arquivos_ordenados = sorted(os.listdir(diretorio_arqs_originais))

        # Percorrer todos os arquivos VBR
        for nome_arquivo in arquivos_ordenados:
            caminho_arq_corrompido = os.path.join(diretorio_arqs_originais, nome_arquivo)

            for log in logs:
                log.write("\n==========================================================\n")
                log.write(f"=== Analisando o arquivo {nome_arquivo} ===\n")
                log.write("==========================================================\n")

            if os.path.isfile(caminho_arq_corrompido): # Arquivo do VBR com erros, que se deseja corrigir    
                conteudo_arq = obter_conteudo_arquivo_corrompido(caminho_arq_corrompido)
                palavras_corrompidas_dict = encontrar_palavras_corrompidas_e_contextos(conteudo_arq)
                procurar_substituicoes_palavras_corrompidas(palavras_corrompidas_dict, lexico)

                escrever_logs(logs, palavras_corrompidas_dict)
        
if __name__ == '__main__':
    main()