from utils.utils import carregar_lexico

def obter_primeira_coluna(caminho_lexico, novo_caminho):
    lexico = carregar_lexico(caminho_lexico)

    with open(novo_caminho, 'w', encoding='utf-8') as novo_lexico:
        for item in lexico:
            novo_lexico.write(item + '\n')

if __name__ == '__main__':
    obter_primeira_coluna('assets/portilexicon-ud.tsv', 'assets/portifirstcol.tsv')