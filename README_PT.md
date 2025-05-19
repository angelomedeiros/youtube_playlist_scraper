# YouTube Playlist Scraper

[English version](README.md) | Versão em Português

Um script Python para baixar metadados de playlists do YouTube usando a YouTube Data API v3. O script pode gerar um único arquivo CSV com todas as playlists ou arquivos separados para cada playlist.

## Funcionalidades

- Baixa metadados de todas as playlists públicas de um canal do YouTube
- Suporta múltiplos canais
- Organiza arquivos em diretórios por canal
- Ignora vídeos indisponíveis
- Gera arquivos CSV com:
  - Nome da playlist
  - Título do vídeo
  - Descrição
  - Duração

## Requisitos

- Python 3.6+
- Google API Python Client
- pandas
- tqdm
- dateutil
- python-dotenv

## Instalação

1. Clone o repositório:

```bash
git clone https://github.com/seu-usuario/youtube-playlist-scraper.git
cd youtube-playlist-scraper
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Obtenha uma chave de API do YouTube:

   - Acesse o [Google Cloud Console](https://console.cloud.google.com/)
   - Crie um novo projeto
   - Ative a YouTube Data API v3
   - Crie uma chave de API

4. Crie um arquivo `.env` na raiz do projeto:

```bash
cp .env.example .env
```

5. Edite o arquivo `.env` e adicione sua chave de API do YouTube:

```
YOUTUBE_API_KEY=sua_chave_api_aqui
```

## Uso

### Comando Básico

```bash
python youtube_playlist_scraper.py
```

### Opções Disponíveis

- `--api_key`: (Opcional) Sua chave da YouTube Data API v3 (se não estiver definida no arquivo .env)
- `-c, --channel`: Handle do canal (ex: "@NomeDoCanal")
- `-p, --playlist`: URL da playlist do YouTube
- `-o, --out`: Nome do arquivo CSV de saída (padrão: "playlists.csv")
- `--split`: Gera um arquivo CSV separado para cada playlist

Nota: Você deve fornecer ou `-c/--channel` ou `-p/--playlist`, mas não ambos.

### Exemplos

1. Baixar todas as playlists de um canal:

```bash
python youtube_playlist_scraper.py -c "@NomeDoCanal"
```

2. Baixar uma única playlist:

```bash
python youtube_playlist_scraper.py -p "https://www.youtube.com/playlist?list=ID_DA_PLAYLIST"
```

3. Gerar um arquivo CSV separado para cada playlist de um canal:

```bash
python youtube_playlist_scraper.py -c "@NomeDoCanal" --split
```

## Estrutura de Arquivos

Os arquivos são organizados da seguinte forma:

```
playlists/
  nome-do-canal/           # Quando usar -c/--channel
    playlist1.csv
    playlist2.csv
    ...
  single_playlists/       # Quando usar -p/--playlist
    playlist1.csv
    ...
```

## Formato do CSV

Os arquivos CSV gerados contêm as seguintes colunas:

- `channel`: Nome do canal
- `playlist`: Nome da playlist
- `videoTitle`: Título do vídeo
- `description`: Descrição do vídeo
- `duration`: Duração do vídeo (formato HH:MM:SS)

## Notas

- O script ignora automaticamente vídeos indisponíveis ou privados
- Playlists vazias são puladas
- O script mostra mensagens informativas sobre vídeos indisponíveis
- Os nomes dos arquivos são sanitizados para remover caracteres inválidos
- A chave de API pode ser definida no arquivo `.env` ou passada via linha de comando

## Limitações

- Requer uma chave de API do YouTube
- Está sujeito às cotas da YouTube Data API v3
- Só pode acessar playlists públicas

## Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests.

## Licença

Este projeto está licenciado sob a MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.
