import streamlit as st
import io

from cria_framefiles import (
    parse_conllu,
    group_by_args,
    group_using_bert,
    group_using_bert_by_verb,
)

# Função para gerar o conteúdo do framefile ignorando rolesets removidos
def framefile_text(rolesets, chosen_verb, descriptions):
    output = io.StringIO()
    output.write(f"Verbo analisado: {chosen_verb}\n\n")

    for args_tuple, data in rolesets.items():
        removido_key = f"removido_{data['roleset_id']}"
        if st.session_state.get(removido_key, False):
            continue  # Ignora roleset removido
        papel_key = f"roles_{data['roleset_id']}"
        # Usa os valores dos inputs, não a lista montada
        edited_roles = []
        for i in range(len(st.session_state.get(papel_key, []))):
            papel_input_key = f"{papel_key}_{i}"
            papel_editado = st.session_state.get(papel_input_key, "")
            if papel_editado.strip():
                edited_roles.append(papel_editado.strip())

        output.write(f"Roleset ID: {data['roleset_id']}\n")
        output.write("Roles:\n")
        if not edited_roles:
            output.write("\t\t-\n")
        for arg in edited_roles:
            output.write(f"\t\t{arg}\n")
        desc = st.session_state.get(f"desc_{data['roleset_id']}", "")
        output.write(f"\nDescrição: {desc}\n")
        output.write("\n---Exemplos de sentenças--- \n\n")
        exemplos_removidos_key = f"ex_rem_{data['roleset_id']}"
        exemplos_removidos = st.session_state.get(exemplos_removidos_key, set())
        
        for example_idx, example in enumerate(data['examples']):
            if example_idx in exemplos_removidos:
                continue  # Ignora exemplo removido
            
            output.write(f"\t{example['sentence']}\n\n")
            argumentos_editados = st.session_state.get(f"args_{data['roleset_id']}_{example_idx}", [])
            for nome_arg, valor_arg in argumentos_editados:
                output.write(f"\t\t{nome_arg}: {valor_arg}\n")
            output.write('*' * 10)
            output.write('\n')
        output.write("-" * 50)
        output.write('\n')
    return output.getvalue()


st.set_page_config(page_title="Framefile Generator", layout="wide")
st.title("Gerador de Framefiles para Verbos")

uploaded_file = st.file_uploader("Selecione o arquivo CONLL-U", type=["conllu"])
if uploaded_file:
    # Lê o arquivo usando sua função
    df = parse_conllu(uploaded_file)

    chosen_verb = st.text_input(
        "Digite o verbo que deseja buscar:",
    ).strip().lower()

    if chosen_verb:
        # Filtra as sentenças que contêm o verbo
        filtered_sentences = df[df["tokens"].apply(
            lambda tokens: any(
                token["upos"] == "VERB" and token["lemma"].lower() == chosen_verb
                for token in tokens
            )
        )]

        if filtered_sentences.empty:
            st.warning(f"Nenhuma sentença encontrada com o verbo '{chosen_verb}'")
        else:
            st.success(f"{len(filtered_sentences)} sentenças encontradas com o verbo '{chosen_verb}'")

            method = st.selectbox(
                "Escolha o método de agrupamento",
                [
                    "Agrupar por papéis/args",
                    "Agrupar com BERT (CLS)",
                    "Agrupar com LLM (prompt)",
                    "Agrupar com BERT (vetor de verbo)"
                ]
            )

            max_sentences = st.number_input(
                "Limite de sentenças por roleset (0 = sem limite)",
                min_value=0, value=0
            )

            rolesets = None

            if method == "Agrupar por papéis/args":
                take_argm = st.checkbox("Considerar ArgMs para diferenciar rolesets")
                if st.button("Executar agrupamento"):
                    rolesets = group_by_args(
                        filtered_sentences,
                        chosen_verb,
                        max_sentences or None,
                        take_argm
                    )
                    st.session_state['rolesets'] = rolesets
            elif method == "Agrupar com BERT (CLS)":
                similarity_threshold = st.slider(
                    "Valor de similaridade do cosseno", min_value=-1.0, max_value=1.0, value=0.7, step=0.01
                )
                if st.button("Executar agrupamento"):
                    rolesets = group_using_bert(
                        filtered_sentences,
                        max_sentences or None,
                        similarity_threshold
                    )
                    st.session_state['rolesets'] = rolesets
            elif method == "Agrupar com LLM (prompt)":
                st.info("Funcionalidade LLM via prompt ainda não está implementada.")
                rolesets = {}
                st.session_state['rolesets'] = rolesets
            elif method == "Agrupar com BERT (vetor de verbo)":
                similarity_threshold = st.slider(
                    "Valor de similaridade do cosseno", min_value=-1.0, max_value=1.0, value=0.7, step=0.01
                )
                if st.button("Executar agrupamento"):
                    rolesets = group_using_bert_by_verb(
                        filtered_sentences,
                        chosen_verb,
                        max_sentences or None,
                        similarity_threshold
                    )
                    st.session_state['rolesets'] = rolesets
            else:
                rolesets = {}
                st.session_state['rolesets'] = rolesets

            # Exibição dos rolesets em abas tipo Cornerstone
            rolesets = st.session_state.get('rolesets', None)
            if rolesets:
                st.subheader("Rolesets detectados")
        
                # Inicializa lista de rolesets ativos na sessão (ANTES de qualquer uso!)
                if 'rolesets_ativos' not in st.session_state:
                    st.session_state['rolesets_ativos'] = [data['roleset_id'] for _, data in rolesets.items()]                
                
                # Botão para baixar o framefile com edições (apenas rolesets não removidos)
                roleset_descriptions = {}
                framefile_content = framefile_text(rolesets, chosen_verb, roleset_descriptions)
                st.download_button(
                    label="Baixar Framefile customizado",
                    data=framefile_content,
                    file_name=f"Framefile-{chosen_verb}-v.txt", 
                    mime="text/plain"
                )

                # Botão para remover o roleset (marcar como removido)
                rolesets_ativos_ids = [data['roleset_id'] for _, data in rolesets.items() if data['roleset_id'] in st.session_state['rolesets_ativos']]
                if len(rolesets_ativos_ids) > 1:
                    roleset_remover = st.selectbox("Selecione o Roleset para remover", rolesets_ativos_ids, key="select_roleset_remover")
                    if st.button("Remover Roleset Selecionado"):
                        removido_key = f"removido_{roleset_remover}"
                        st.session_state[removido_key] = True
                        st.rerun()
                else:
                    st.info("Não é possível remover o último roleset. Adicione outro para poder remover este.")

                
                if st.button("Criar novo Roleset"):
                    # Gera novo id único (maior id + 1)
                    if rolesets:
                        novo_id = max([data['roleset_id'] for _, data in rolesets.items()]) + 1
                    else:
                        novo_id = 1
                    # Adiciona novo roleset vazio
                    rolesets[(tuple(), novo_id)] = {
                        'roleset_id': novo_id,
                        'examples': [],
                    }
                    st.session_state['rolesets_ativos'].append(novo_id)
                    st.session_state['rolesets'] = rolesets
                    st.rerun()

                # Atualiza rolesets_ativos, removendo/restaurando conforme session_state[removido_key]
                for args_tuple, data in rolesets.items():
                    removido_key = f"removido_{data['roleset_id']}"
                    if st.session_state.get(removido_key, False):
                        if data['roleset_id'] in st.session_state['rolesets_ativos']:
                            st.session_state['rolesets_ativos'].remove(data['roleset_id'])
                    else:
                        if data['roleset_id'] not in st.session_state['rolesets_ativos']:
                            st.session_state['rolesets_ativos'].append(data['roleset_id'])

                # Filtra apenas rolesets ativos e únicos
                abas_validas = [
                    (args_tuple, data)
                    for args_tuple, data in rolesets.items()
                    if data['roleset_id'] in st.session_state['rolesets_ativos']
                ]
                
                # Cria uma aba para cada roleset ativo
                tabs = st.tabs([f"Roleset {data['roleset_id']}" for _, data in abas_validas])
                roleset_descriptions = {}

                for idx, (args_tuple, data) in enumerate(abas_validas):
                    with tabs[idx]:
                        papel_key = f"roles_{data['roleset_id']}"
                        removido_key = f"removido_{data['roleset_id']}"

                        # Inicializa papéis e estado de removido
                        if papel_key not in st.session_state:
                            st.session_state[papel_key] = list(args_tuple)
                        if removido_key not in st.session_state:
                            st.session_state[removido_key] = False

                        # Se removido, mostra aviso e botão para restaurar
                        if st.session_state[removido_key]:
                            st.warning("Este roleset foi removido e não será exportado.")
                            if st.button("Restaurar Roleset", key=f"restaurar_{data['roleset_id']}"):
                                st.session_state[removido_key] = False
                                st.rerun()  # Força rerun para atualizar interface
                        else:
                            st.markdown(f"### Roleset {data['roleset_id']}")
                            # Edição dos papéis semânticos...
                            st.markdown("**Papéis semânticos (edite ou remova):**")
                            papel_novo = []
                            for i, papel in enumerate(st.session_state[papel_key]):
                                col1, col2 = st.columns([4,1])
                                with col1:
                                    papel_editado = st.text_input(f"Papel {i+1}", value=papel, key=f"{papel_key}_{i}")
                                with col2:
                                    if st.button("Remover", key=f"remove_{papel_key}_{i}"):
                                        del st.session_state[papel_key][i]
                                        st.rerun()  # Atualiza imediatamente a interface
                                        continue
                                if papel_editado.strip():     
                                    papel_novo.append(papel_editado.strip())
                            st.session_state[papel_key] = papel_novo

                            novo_papel = st.text_input("Adicionar novo papel", key=f"add_{papel_key}")
                            if st.button("Adicionar papel", key=f"btn_add_{papel_key}"):
                                if novo_papel.strip():
                                    st.session_state[papel_key].append(novo_papel.strip())
                                    st.rerun()  # Atualiza interface imediatamente
                            # --- FIM DA EDIÇÃO DE PAPÉIS SEMÂNTICOS ---

                            st.markdown("**Exemplos de uso:**")
                            # Inicializa lista de exemplos removidos por roleset
                            exemplos_removidos_key = f"ex_rem_{data['roleset_id']}"
                            if exemplos_removidos_key not in st.session_state:
                                st.session_state[exemplos_removidos_key] = set()
                            
                            for example_idx, example in enumerate(data['examples']):
                                removido = example_idx in st.session_state[exemplos_removidos_key]
                                
                                st.markdown(f"> {example['sentence']}")
                                if example['arguments']:
                                    st.markdown("**Argumentos:**")
                                    argumentos_editados = []
                                    argumentos_lista = list(example['arguments'].items())
                                    for arg_idx, (arg, form) in enumerate(argumentos_lista):
                                        nome_key = f"nomearg_{data['roleset_id']}_{example_idx}_{arg_idx}"
                                        valor_key = f"valorarg_{data['roleset_id']}_{example_idx}_{arg_idx}"
                                        cols = st.columns([1,2])
                                        with cols[0]:
                                            nome_arg = st.text_input("Nome do argumento", value=arg, key=nome_key)
                                        with cols[1]:
                                            valor_arg = st.text_input("Valor do argumento", value=form, key=valor_key)
                                        argumentos_editados.append((nome_arg, valor_arg))
                                    # Salva os argumentos editados no session_state para exportação
                                    st.session_state[f"args_{data['roleset_id']}_{example_idx}"] = argumentos_editados
                                
                                if removido:
                                    st.warning("Este exemplo está marcado como removido e não será exportado.")
                                    if st.button("Restaurar exemplo", key=f"restaurar_ex_{data['roleset_id']}_{example_idx}"):
                                        st.session_state[exemplos_removidos_key].remove(example_idx)
                                        st.rerun()

                                else:
                                    if st.button("Remover exemplo", key=f"rem_ex_{data['roleset_id']}_{example_idx}"):
                                        st.session_state[exemplos_removidos_key].add(example_idx)
                                        st.rerun()  # Atualiza a interface imediatamente

                            # --- ADIÇÃO DE NOVO EXEMPLO ---
                            st.markdown("**Adicionar novo exemplo:**")

                            # Inicializa o campo da sentença, se ainda não existe
                            nova_sentenca_key = f"nova_sent_{data['roleset_id']}"
                            novo_args_key = f"novo_args_{data['roleset_id']}"

                            # Inicializa se não existir
                            if nova_sentenca_key not in st.session_state:
                                st.session_state[nova_sentenca_key] = ""
                            if novo_args_key not in st.session_state:
                                st.session_state[novo_args_key] = []

                            # Limpa se a flag estiver ativa
                            if st.session_state.get(f"limpar_{nova_sentenca_key}", False):
                                st.session_state[nova_sentenca_key] = ""
                                st.session_state[f"limpar_{nova_sentenca_key}"] = False

                            if st.session_state.get(f"limpar_{novo_args_key}", False):
                                st.session_state[novo_args_key] = []
                                st.session_state[f"limpar_{novo_args_key}"] = False

                            # Campo para sentença
                            nova_sentenca = st.text_input("Sentença do exemplo", key=nova_sentenca_key, value="")

                            # Campos para argumentos do novo exemplo
                            if novo_args_key not in st.session_state:
                                st.session_state[novo_args_key] = []

                            st.markdown("Adicione argumentos (nome e valor):")
                            col_arg_nome, col_arg_valor = st.columns(2)
                            novo_nome_arg = col_arg_nome.text_input("Nome do argumento", key=f"novo_nome_arg_{data['roleset_id']}")
                            novo_valor_arg = col_arg_valor.text_input("Valor do argumento", key=f"novo_valor_arg_{data['roleset_id']}")

                            if st.button("Adicionar argumento ao exemplo", key=f"add_arg_ex_{data['roleset_id']}"):
                                if novo_nome_arg.strip() and novo_valor_arg.strip():
                                    st.session_state[novo_args_key].append((novo_nome_arg.strip(), novo_valor_arg.strip()))
                                    st.rerun()

                            # Lista de argumentos já adicionados
                            for i, (nome, valor) in enumerate(st.session_state[novo_args_key]):
                                st.write(f"{nome}: {valor}")
                                if st.button("Remover argumento", key=f"remover_novo_arg_{data['roleset_id']}_{i}"):
                                    del st.session_state[novo_args_key][i]
                                    st.rerun()

                            # Botão para adicionar o novo exemplo ao roleset
                            if st.button("Adicionar exemplo ao roleset", key=f"add_ex_{data['roleset_id']}"):
                                if st.session_state[nova_sentenca_key].strip():
                                    novo_exemplo = {
                                        'sentence': st.session_state[nova_sentenca_key].strip(),
                                        'arguments': {nome: valor for nome, valor in st.session_state[novo_args_key]}
                                    }
                                    # Adiciona no objeto 'data['examples']'
                                    data['examples'].append(novo_exemplo)
                                    # Sinaliza para limpar na próxima execução
                                    st.session_state[f"limpar_{nova_sentenca_key}"] = True
                                    st.session_state[f"limpar_{novo_args_key}"] = True
                                    st.rerun()

                            # Recupera o valor atual do campo e o último valor salvo
                            desc_key = f"desc_{data['roleset_id']}"
                            desc_atual = st.text_area(
                                f"Descrição para o Roleset {data['roleset_id']}",
                                key=desc_key,
                                value=st.session_state.get(desc_key, "")
                            )
                