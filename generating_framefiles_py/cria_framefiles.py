import numpy as np
import pandas as pd
import torch

from typing import Union
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity

def parse_conllu(file_path) -> pd.DataFrame:
    """"
    Função para extrair as informações do formato CONLL-U para um dataframe do pandas.
    Aceita tanto caminho do arquivo (str) quanto objeto de arquivo (Streamlit UploadedFile).

    Args:
        file_path (str): o caminho para o arquivo CONLL-U do qual se extrairão os dados.
    Returns:
        pd.Dataframe: estrutura de dataframe do pandas para acesso facilitado às colunas.
    """
    sentences = []
    sentence = []

    # Verifica se é um arquivo em memória (tem método 'read'), como o do Streamlit
    if hasattr(file_path, "read"):
        lines = file_path.read().decode("utf-8").splitlines()
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()


    for line in lines:
        line = line.strip()
        if line.startswith("# sent_id"):
            sent_id = line.split(" = ")[1]
        elif line.startswith("# text"):
            text = line.split(" = ")[1]
        elif line == "":
            if sentence:
                sentences.append({"sent_id": sent_id, "text": text, "tokens": sentence})
                sentence = []
        elif not line.startswith("#"):
            parts = line.split("\t")
            if len(parts) >= 10:
                token_info = {
                    "id": parts[0],
                    "form": parts[1],
                    "lemma": parts[2],
                    "upos": parts[3],
                    "xpos": parts[4],
                    "feats": parts[5],
                    "head": parts[6],
                    "deprel": parts[7],
                    "deps": parts[8],
                    "misc": parts[9]
                }
                sentence.append(token_info)

    return pd.DataFrame(sentences)

def print_sentences(filtered_sentences:pd.DataFrame) -> None:
    """
    Exibe informações das sentenças filtradas por conter o verbo de interesse.

    Args:
        filtered_sentences (pd.DataFrame): estrutura de dataframe pandas com as sentenças selecionadas.
    """

    for _, row in filtered_sentences.iterrows():
            print(f"{row['sent_id']}: {row['text']}\n")

def choose_sentence_grouping_method() -> int:
    """
    Permite ao usuário escolher um dos três métodos de agrupamentos possíveis, sendo 1 o método ingênuo de agrupamento por argumentos, 2 usando BERT e 3 usando LLM com prompt.

    Returns:
        int: o número do método desejado para agrupar sentenças.
    """
    while True:
        try:
            method = int(input(
                """Escolha a opção para criar grupos:\n
                1 -> Agrupar sentenças por papéis/args dos verbos\n
                2 -> Agrupar sentenças com BERT (cls)\n
                3 -> Agrupar usando LLM com prompt\n
                4 -> Agrupar sentenças com BERT - vetor de verbo\n""")
            )
            if method in [1, 2, 3, 4]:
                break
            print("Opção inválida!")
        except ValueError:
            print("Valor inválido. Tente novamente.\n")

    print(f"Opção escolhida: {method}\n")
    return method

def limit_number_of_sentences_per_roleset() -> Union[int, None]:
    """
    Interage com o usuário para potencialmente limitar o número de sentenças máximo por exemplo de uso de um roleset. Se o usuário não deseja limitar, o valor será None e todas as sentenças armazenadas são consideradas.

    Returns:
        Optional[int]: Um inteiro representando o limite de sentenças, ou None se não houver limite.
    """
    while True:
        max_sentences_per_roleset = input("Limite de sentenças por roleset (se não deseja limitar, enter): ")
        if max_sentences_per_roleset == "":
            max_sentences_per_roleset = None
            break
        try:
            max_sentences_per_roleset = int(max_sentences_per_roleset)
            if max_sentences_per_roleset > 0:
                break
            elif max_sentences_per_roleset <= 0:
                print("Por favor, entre um número maior que zero!")
        except ValueError:
            print("Você digitou um limite inválido. Tente novamente.\n")
    
    return max_sentences_per_roleset

def choose_to_consider_argm() -> bool:
    """
    Fornece a opção ao usuário de considerar os ArgMs para criar novos rolesets para agrupar.

    Returns:
        bool: True se usuário deseja distinguir rolesets levando em conta os ArgMs, False caso contrário.
    """
    while True:
        take_argm_to_rolesets = input("Deseja considerar os ArgMs para diferenciar os rolesets? (s/n): ").strip().lower()
        if take_argm_to_rolesets in ["s", "n"]:
            take_argm_to_rolesets = (take_argm_to_rolesets == "s")
            break
        else:
            print("Entrada inválida. Por favor, responda com 's' ou 'n'.")
    return take_argm_to_rolesets

def choose_cosine_similarity_threshold() -> float:
    """
    Para a opção de agrupamento usando BERT (2), o usuário deve indicar o limiar de aproximação por medida de cosseno, variando de -1 a 1.

    Returns:
        float: o valor de similaridade do cosseno a ser considerado ao comparar a proximidade de sentido das sentenças.
    """
    while True:
            try:
                similarity_threshold = float(input("Digite valor de similaridade do cosseno: "))
                if -1.0 <= similarity_threshold <= 1.0:
                    print(f"Valor escolhido: {similarity_threshold}")
                    break
                print("Valor deve estar entre -1 e 1.")
            except ValueError:
                print("Valor inválido, tente novamente.")
    return similarity_threshold

def group_by_args(filtered_sentences:pd.DataFrame, chosen_verb:str, max_sentences_per_roleset:int, take_argm_to_rolesets:bool) -> dict:
    """
    Procura relações com o verbo desejado dentro das sentenças selecionadas e as agrupa de acordo com os mesmos argumentos.
    Args:
        filtered_sentences (pd.DataFrame): sentenças filtradas que contêm o verbo chosen_verb.

        chosen_verb (str): verbo principal da sentença, a partir do qual buscamos relações de dependência.

        max_sentences_per_roleset (int): quantidade máxima de sentenças buscadas para cada roleset. É None caso o usuário não limite, e traz todos os resultados encontrados. Caso não tenha essa quantidade de sentenças (tenha menos), todas elas são guardadas e exibidas.

        take_argm_to_rolesets (bool): flag que indica se os ArgMs formarão ou não novos rolesets.
        
    Returns:
        dict: dicionário com os diferentes rolesets - id, quais argumentos possui e exemplos de sentenças.
    """
    rolesets = {}  # Dicionário para armazenar roleset ids

    for _, row in filtered_sentences.iterrows():
        print("-" * 25)
        print(f"Sentença analisada atualmente:\n{row}\n")
        # Vamos coletar todos os argumentos para o verbo escolhido
        args = set()  # Conjunto para garantir que não haja argumentos duplicados
        verb_id = None  # Encontrar o ID do verbo escolhido
        arguments_info = {}  # Dicionário para armazenar os argumentos de cada exemplo
        

        for token in row["tokens"]:
            # Capturar o id do verbo para achar todos os args relacionados a ele
            if token["lemma"].lower() == chosen_verb and token["upos"] == "VERB":
                verb_id = token["id"]
                print(f"Id do verbo na sentença: {verb_id}")
                arguments_info["Rel"] = token["form"]
            
            if "Arg" in token["misc"]: # Um token faz um papel de arg. É em relação ao verbo?
                # Procurando argumentos relacionados ao verbo escolhido
                for arg in token["misc"].split("|"):
                    arg = arg.split(":")
                    if len(arg) > 1 and f"Arg" in arg[0] and arg[1] == str(verb_id): # id do verbo deve ser exatamente o mesmo do arg
                        if arg[0][3:].isdigit():  # desconsiderar tmp, M, ...
                            arg_role = arg[0]  # Nome do argumento (ex: Arg0, Arg1, etc.)
                            print(arg_role)
                            args.add(arg_role)
                            arguments_info[arg_role] = token["form"] # Armazenando a palavra que realiza o papel do arg na sentença
                        else:
                            # Se for do tipo ArgM, Arg-Tmp, etc, apenas adiciona ao arguments_info, sem modificar rolesets
                            print(f"Argumento não numérico encontrado: {arg}")
                            arguments_info[arg[0]] = token["form"]

                            # Se o usuário desejar, os args modificadores serão determinantes como novos rolesets também
                            if take_argm_to_rolesets:
                                args.add(arg[0])  # arg[0] é tipo 'ArgM-loc', 'ArgM-tmp' etc.

            
        # Ordenando os argumentos e criando uma tupla
        args_tuple = tuple(sorted(args))  # Ordena os argumentos e os transforma em tupla
        print(f"Args no final: {args_tuple}")

        # Usamos os argumentos para gerar um roleset id único
        if args_tuple not in rolesets:
            # chave do dicionário: a tupla de argumentos (garantindo que seja única)
            rolesets[args_tuple] = {"roleset_id": len(rolesets) + 1, "examples": [], "example_amt": 0}  # Atribuindo um roleset id único e inicializando a lista de exemplos

        # Atribuindo o roleset id à sentença e adicionando a sentença à lista de exemplos
        row["roleset_id"] = rolesets[args_tuple]["roleset_id"] # Para ter isso no DF caso seja necessário

        # limitar o nro de sentenças se desejado
        current_count = rolesets[args_tuple]["example_amt"]
        if max_sentences_per_roleset is None or current_count < max_sentences_per_roleset: 
            rolesets[args_tuple]["examples"].append({"sentence": row["text"], "arguments": arguments_info})  # Adicionando a sentença como exemplo desse roleset id, junto com o arg
            rolesets[args_tuple]["example_amt"] += 1

    return rolesets

def calculate_similarity_matrix(verb_vector):
    # Somente os vetores válidos
    valid_vectors = [v for v in verb_vector if v is not None]

    similarity_matrix = cosine_similarity(valid_vectors)

    print("Matriz de similaridade entre os verbos:")
    print(np.round(similarity_matrix, 2))

def group_using_bert(filtered_sentences:pd.DataFrame, max_sentences_per_roleset:int, similarity_threshold:float) -> dict:
    """
    Agrupa sentenças com base na similaridade de embeddings do modelo BERT (token [CLS]).

    Args:
        filtered_sentences (pd.DataFrame): sentenças filtradas que contêm o verbo escolhido e principal da sentença, a partir do qual buscamos relações de dependência.

        max_sentences_per_roleset (int): quantidade máxima de sentenças buscadas para cada roleset. É None caso o usuário não limite, e traz todos os resultados encontrados. Caso não tenha essa quantidade de sentenças (tenha menos), todas elas são guardadas e exibidas.

        similarity_threshold (float): valor para similaridade de cossenos, que vai de -1 a 1.
        
    Returns:
        dict: dicionário com os diferentes rolesets - id, quais argumentos possui e exemplos de sentenças.
    """
    # Carrega o modelo pré-treinado (BERTimbau base)
    tokenizer = AutoTokenizer.from_pretrained("neuralmind/bert-base-portuguese-cased") # cria tokens a partir de frases
    model = AutoModel.from_pretrained("neuralmind/bert-base-portuguese-cased") # retorna embeddings dos tokens

    sentence_texts = filtered_sentences["text"].tolist() # nossas sentenças

    # Vetores CLS para cada sentença 
    cls_vectors = []
    for text in sentence_texts:
        # tokenizer: texto -> tokens -> word embedding para os tokens (vetores de 768 características)
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128, padding=True)
        with torch.no_grad(): # nao calcule gradientes
            outputs = model(**inputs)
        cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze().numpy()  # Vetor do token CLS, com 768 valores, representando semanticamente a sentença toda
        cls_vectors.append(cls_embedding)
    
    # Agrupar por similaridade
    grouped = []
    used = [False] * len(cls_vectors)

    for i in range(len(cls_vectors)):
        if used[i]:
            continue
        group = [i]
        used[i] = True
        for j in range(i + 1, len(cls_vectors)):
            if not used[j]:
                sim = cosine_similarity([cls_vectors[i]], [cls_vectors[j]])[0][0]
                if sim >= similarity_threshold:
                    group.append(j)
                    used[j] = True
        grouped.append(group)

    # Criar o dicionário rolesets no mesmo formato que a opção 1
    rolesets = {}
    for idx, group in enumerate(grouped):
        examples = []
        for i in group[:max_sentences_per_roleset or len(group)]:
            examples.append({
                "sentence": filtered_sentences.iloc[i]["text"],
                "arguments": {}
            })
        rolesets[("BERT-sense-" + str(idx+1),)] = {
            "roleset_id": idx + 1,
            "examples": examples,
            "example_amt": len(examples)
        }

    return rolesets


def group_using_bert_by_verb(filtered_sentences:pd.DataFrame, chosen_verb:str, max_sentences_per_roleset:int, similarity_threshold:float) -> dict:
    """
    Agrupa sentenças com base na similaridade de embeddings do modelo BERT (usando vetor do verbo principal).

    Args:
        filtered_sentences (pd.DataFrame): sentenças filtradas que contêm o verbo escolhido e principal da sentença, a partir do qual buscamos relações de dependência.
        chosen_verb (str): verbo principal (forma lematizada) usado como âncora semântica.
        max_sentences_per_roleset (int): quantidade máxima de sentenças buscadas para cada roleset. É None caso o usuário não limite, e traz todos os resultados encontrados. Caso não tenha essa quantidade de sentenças (tenha menos), todas elas são guardadas e exibidas.
        similarity_threshold (float): valor mínimo para similaridade de cossenos, que vai de -1 a 1, para formar grupos.

    Returns:
        dict: dicionário com agrupamentos de diferentes rolesets - id, quais argumentos possui e exemplos de sentenças. 
    """

    # Carrego o modelo
    tokenizer = AutoTokenizer.from_pretrained("neuralmind/bert-base-portuguese-cased")
    model = AutoModel.from_pretrained("neuralmind/bert-base-portuguese-cased")

    verb_vectors = []

    # Extrair o vetor do verbo principal de cada sentença
    for _, row in filtered_sentences.iterrows():
        text = row["text"]
        tokens = row["tokens"]

        # Encontra o token do verbo principal (por lema e UPOS)
        verb_token = next((t for t in tokens if t["lemma"].lower() == chosen_verb and t["upos"] == "VERB"), None)
        if not verb_token:
            verb_vectors.append(None)
            continue

        # Encontrar o verbo na sentença pra localizar token BERT
        verb_form = verb_token["form"]
        verb_char_index = text.lower().find(verb_form.lower())

        # Tokeniza a sentença com offset_mapping (qual token é o verbo)
        encoded = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=128,
            padding=True,
            return_offsets_mapping=True
        )
        offsets = encoded.pop("offset_mapping")[0]  # Remove offset para não ser passado ao model (não aceita)

        with torch.no_grad():
            outputs = model(**encoded)

        # Encontra o índice do token correspondente ao verbo
        verb_token_index = None
        for i, (start, end) in enumerate(offsets.tolist()):
            if start <= verb_char_index < end:
                verb_token_index = i
                break

        # Se não encontrar, usa CLS como fallback
        if verb_token_index is None:
            vector = outputs.last_hidden_state[:, 0, :].squeeze().numpy() # token CLS
        else:
            vector = outputs.last_hidden_state[0, verb_token_index, :].numpy() # token do verbo

        # Guardar todos os vetores dos verbos para fazer o agrupamento por similaridade depois
        verb_vectors.append(vector)

    calculate_similarity_matrix(verb_vectors)

    # Filtrar vetores None
    valid_idx_map = [i for i, v in enumerate(verb_vectors) if v is not None]
    valid_vectors = [verb_vectors[i] for i in valid_idx_map]

    if not valid_vectors:
        return {}
    
    # Matriz de similaridade - checa todos os vetores BERT do verbo
    similarity_matrix = cosine_similarity(valid_vectors)

    # Construir grafo (lista de adjacência)
    n = len(valid_vectors)
    adj = {i: [] for i in range(n)}

    # Para cada par de sentenças i, j
    for i in range(n):
        for j in range(i + 1, n):
            # elas são suficientemente próximas semanticamente?
            if similarity_matrix[i][j] >= similarity_threshold:
                # conectar i e j (pertencem ao mesmo grupo de sentido de sentença)
                adj[i].append(j)
                adj[j].append(i)

    # Busca DFS para componentes conexos (quais sentenças já foram visitadas)
    visited = [False] * n
    groups = []

    # Encontrar todas as sentenças conectadas entre si
    def dfs(node, group):
        visited[node] = True
        group.append(node)
        for neighbor in adj[node]:
            if not visited[neighbor]:
                dfs(neighbor, group)

    for i in range(n):
        if not visited[i]:
            group = []
            dfs(i, group) # preenche group com todas as sentenças conectadas a i
            groups.append(group) # group é um roleset
    
    # Se duas sentenças estão conectadas por uma cadeia de similaridade (mesmo que indireta), 
    # elas serão agrupadas em um mesmo group, ou seja, mesmo roleset.

    # Mapear grupos para índices originais do dataframe (porque filtrei os None pra montar o grafo)
    mapped_groups = []
    for group in groups:
        mapped_groups.append([valid_idx_map[i] for i in group])

    # Monta o dicionário no formato esperado
    rolesets = {}
    for idx, group in enumerate(mapped_groups):
        examples = []
        for i in group[:max_sentences_per_roleset or len(group)]:
            examples.append({
                "sentence": filtered_sentences.iloc[i]["text"],
                "arguments": {}
            })
        rolesets[("BERT-VERB-sense-" + str(idx + 1),)] = {
            "roleset_id": idx + 1,
            "examples": examples,
            "example_amt": len(examples)
        }

    return rolesets

def print_roleset(args_tuple:tuple, data:dict) -> None:
    """
    Exibe informações de cada roleset: o id, os 'roles' e os exemplos associados a ele.

    Args:
        args_tuple (tuple): chave do dicionário de rolesets, contém os argumentos / papéis semânticos desse roleset.

        data (dict): valor do dicionário de rolesets, contém o roleset id e os exemplos de sentenças com os args desse roleset.
    """

    print(f"Roleset ID: {data['roleset_id']}")

    print("Roles:")
    if not args_tuple:
        print("\t-")
    for arg in args_tuple:
        print(f"\t{arg}")  

    # Exibindo os exemplos de sentenças com seus argumentos
    print("\n---Exemplos de sentenças--- \n")
    for example in data['examples']:
        print(f"\t{example['sentence']}\n")

        # Exibindo os argumentos relacionados à sentença
        sorted_arguments = sorted(
            example['arguments'].items(),
            key=lambda x: (
                int(x[0][3:]) if x[0][3:].isdigit() else float('inf'),  # Ordena números como Arg0, Arg1, etc.
                x[0]  # Para garantir que os argumentos não numéricos, como ArgM-loc, Arg-Tmp, etc., apareçam depois
            )
        )
        for arg, form in sorted_arguments:
            print(f"\t\t{arg}: {form}")
        print('*' * 10)

    print("-" * 50)  # Separador entre os rolesets

def write_file(rolesets:dict, chosen_verb:str) -> None:
    """"
    Esta função escreve um arquivo de nome 'Framefile-[chosen_verb]-v.txt' como framefile do verbo passado, considerando seus diferentes conjuntos de argumentos.

    Args:
        rolesets (dict): tipos de argumentos considerados no modo como o verbo é empregado em cada sentença.

        chosen_verb (str): o verbo analisado nas sentenças.
    """
    with open(f"Framefile-{chosen_verb}-v.txt", "w", encoding="utf-8") as file:
        for args_tuple, data in rolesets.items():
            file.write(f"Roleset ID: {data['roleset_id']}\n")
            file.write("Roles:\n")
            if not args_tuple:
                file.write("\t\t-\n")
            for arg in args_tuple:
                file.write(f"\t\t{arg}\n")
            file.write("\n---Exemplos de sentenças--- \n\n")
            for example in data['examples']:
                file.write(f"\t{example['sentence']}\n\n")

                sorted_arguments = sorted(
                    example['arguments'].items(),
                    key=lambda x: (
                        int(x[0][3:]) if x[0][3:].isdigit() else float('inf'),  # Ordena números como Arg0, Arg1, etc.
                        x[0]  # Para garantir que os argumentos não numéricos, como ArgM-loc, Arg-Tmp, etc., apareçam depois
                    )
                )

                for arg, form in sorted_arguments:
                    file.write(f"\t\t{arg}: {form}\n")
                file.write('*' * 10)
                file.write('\n')
            file.write("-" * 50)
            file.write('\n')


def main():
    # Caminho do arquivo CONLL-U, de entrada
    file_path = "PBP-classic-complete.conllu"

    # Criando o DataFrame
    df = parse_conllu(file_path)

    # Ler verbo para o qual se deseja fazer um framefile
    chosen_verb = input("Digite o verbo que deseja buscar: ").strip().lower()
    print(chosen_verb)
    print('-' * 25)

    # Acessar arquivo PBP e buscar todas as sentenças (em formato conll-u) que contenham o verbo de interesse
        # Filtrar sentenças que contêm o verbo desejado no lema
    filtered_sentences = df[df["tokens"].apply(lambda tokens: any(token["upos"] == "VERB" and token["lemma"].lower() == chosen_verb for token in tokens))]

    # Exibir as sentenças filtradas
    if filtered_sentences.empty:
        print(f"\nNenhuma sentença encontrada com o verbo '{chosen_verb}'. O programa será encerrado.")
        return
    else:
        print(f"\nSentenças contendo o verbo '{chosen_verb}' foram encontradas.\n")
    
    rolesets = None
    
    method = choose_sentence_grouping_method()
    repeat = True
    while repeat:
        max_sentences_per_roleset = limit_number_of_sentences_per_roleset()

        # Criar grupos de sentenças de sentidos diferentes
        # opção 1: agrupar sentenças por papéis/args que os verbos tenham (heurística ingênua)
        if method == 1:
            take_argm_to_rolesets = choose_to_consider_argm()
            rolesets = group_by_args(filtered_sentences, chosen_verb, max_sentences_per_roleset, take_argm_to_rolesets)
        # opção 2: usar um modelo de língua (BERT?) para agrupar as sentenças
        elif method == 2:
            similarity_threshold = choose_cosine_similarity_threshold()
            rolesets = group_using_bert(filtered_sentences, max_sentences_per_roleset, similarity_threshold)
        # opção 3: usar um LLM (via prompt) para agrupar as sentenças
        elif method == 3:
            print("TODO: usar um LLM (via prompt) para agrupar as sentenças")
            rolesets = {}
        elif method == 4:
            similarity_threshold = choose_cosine_similarity_threshold()
            rolesets = group_using_bert_by_verb(filtered_sentences, chosen_verb, max_sentences_per_roleset, similarity_threshold)
        else:
            print("Algo inesperado ocorreu e o programa será encerrado.")

        # -------------------------------------------------------------
        # Exibir o resultado atual dos rolesets e seus exemplos
        print('-' * 25)
        print(f"\nResultado dos rolesets possíveis\n".upper())
        print('-' * 25)
        for args_tuple, data in rolesets.items():
            print_roleset(args_tuple, data)
        
        repeat = input("Executar novamente?\n\ts -> Sim, mesmo tipo de agrupamento, com novos parâmetros\n\tm -> Sim, mudar configuração/método de agrupamento\n\tn -> Não, escrever dados em arquivo e encerrar.\n ")
        if repeat == 'n':
            repeat = False
        elif repeat == 'm':
            print("Mudando o método de agrupamento...")
            method = choose_sentence_grouping_method()

    write_file(rolesets, chosen_verb)
    print(f"Arquivo de Framefile do verbo {chosen_verb} foi escrito! Encerrando...")

if __name__ == "__main__":
    main()