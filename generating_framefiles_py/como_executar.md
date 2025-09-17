# Geração de framefiles

### Resumo
Este diretório pretende gerar framefiles e facilitar o trabalho de um linguista anotador, pré-preenchendo os campos do framefile através de algumas estratégias e, ainda assim, permitindo adições, edições e remoções pelo linguista humano.

### Requisitos e instalações
É preciso, primeiramente, clonar o repositório com `git clone` ou realizar o <i>download</i> do repositório comprimido (.zip).

Para a utilização do repositório de modo offline, uma vez clonado ou baixado, é necessário garantir que o usuário possua o interpretador Python disponível. As instruções para esta instalação podem ser visualizadas em https://www.python.org/downloads/. Para os testes realizados, foi utilizado Python na versão 3.13.2.

Garanta também a existência do instalador de pacotes pip, cujas instruções de instalação podem ser seguidas em https://pypi.org/project/pip/.

**Caso você esteja utilizando o sistema operacional Linux, indique python3 e pip3.

```
python3 --version
# Se não encontrada versão do Python
sudo apt update
sudo apt install python3

pip3 --version
# Se não encontrada versão do pip
apt install python3-pip 
```

Além disso, é recomendável criar e ativar um ambiente virtual com o uso de venv.

```
# Vá para o repositório
cd poetisa/generating_framefiles_py/

python3 -m venv venv
source venv/bin/activate # Linux/macOS
venv\Scripts\activate    # Windows
```

E, então, instale as dependências listadas no arquivo de requisitos `requirements.txt` com o comando:
```
pip3 install -r requirements.txt
```

O diretório utiliza bibliotecas úteis para aplicações de Inteligência Artificial, além das mais comuns para estruturar os dados de forma viável para o seu processamento, e do Streamlit para a interface web.

**Rode <b>pip3 freeze</b> se quiser garantir que os requisitos estão instalados.

Após estas configurações, a aplicação deve estar pronta para execução.

### Execução

Uso offline: No terminal, garantindo que você esteja com o ambiente virtual ativado e no diretório `generating_framefiles_py`, execute:
```
streamlit run app.py
```

Isso permitirá o acesso à aplicação pela interface web do Streamlit, geralmente acessível em http://localhost:8501 no seu navegador.

### Na interface web
No diretório de `generating_framefiles_py`, foi colocado um arquivo `.conllu`, mas você pode utilizar outros. 

Adicione o arquivo desejado e escolha o verbo que você deseja analisar.

Feito isto, escolha o método de agrupamento dos sentidos de verbos.

Então, aguarde. Será gerado um resultado pré-preenchido que poderá ser editado por você posteriormente. Para garantir que suas mudanças sejam salvas, ao terminar uma modificação, entre `Ctrl` + `Enter` no campo.

Assim que terminar as alterações, basta exportar o conteúdo em 'Baixar Framefile customizado'. O download será iniciado.