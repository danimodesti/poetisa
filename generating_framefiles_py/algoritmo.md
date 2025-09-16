Momento de acionamento do algoritmo abaixo: usuário usando a interface hipotética (cornerstone++), criando um novo framefile


*** ALGORITMO DE BUSCA DE DADOS PARA CRIAÇÃO DE FRAMEFILES ***

Entrada:
- PBP versão clássico completo

ler verbo (para o qual se deseja fazer um framefile) do usuário (entrada via interface)
acessar arquivo PBP e buscar todas as sentenças (em formato conll-u) que contenham o verbo de interesse
montar dataframe com as sentenças buscadas
criar grupos de sentenças de sentidos diferentes 
    - opção 1: agrupar sentenças por papeis/args que os verbos tenham (heurística ingênua)
    - opção 2: usar um modelo de língua (BERT?) para agrupar as sentenças
    - opção 3: usar um LLM (via prompt) para agrupar as sentenças
para cada grupo de sentenças (formado por qualquer que tenha sido a opção acima)
    montar o roleset id, incluindo os "roles" e os exemplos
montar um arquivo de framefile com os roleset ids acima e as informações associadas (roles e exemplos)
retornar esse arquivo para a interface hipotética (cornerstone++), que o carregará na tela para o usuário revisar/adicionar exemplos/remover exemplos


