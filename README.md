# ClearFiles Professional 🚀

**ClearFiles** é uma ferramenta de código aberto para Windows, desenvolvida em Python, projetada para automatizar a limpeza de diretórios e recuperação de espaço em disco de forma inteligente e agendada.

![Version](https://img.shields.io/badge/version-2.1-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## ✨ Funcionalidades

- 📁 **Gerenciamento de Pastas**: Adicione múltiplos diretórios para limpeza simultânea.
- ⚙️ **Automação Completa**:
  - Limpeza ao iniciar o Windows (Logon).
  - Limpeza ao desligar o computador (Shutdown).
  - Limpeza em intervalos regulares (ex: a cada 60 minutos).
- 📊 **Feedback em Tempo Real**: Visualize a quantidade de espaço liberado e o status do sistema.
- 🌙 **Interface Moderna**: UI escura baseada em `CustomTkinter` para uma experiência de usuário premium.
- 🔇 **Modo Silencioso**: Execução em segundo plano via Agendador de Tarefas do Windows.

## 🛠️ Tecnologias Utilizadas

- **Python 3**: Linguagem principal.
- **CustomTkinter**: Framework para a interface gráfica moderna.
- **Pillow**: Processamento de imagens/logos.
- **Windows Task Scheduler**: Integração nativa para agendamentos.

## 🚀 Como Executar

### Pré-requisitos
- Python 3.8 ou superior instalado.

### Instalação
1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/clearfiles.git
   cd clearfiles
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Execute a aplicação:
   ```bash
   python main.py
   ```

## 📦 Gerando o Executável (.exe)

Para distribuir a aplicação como um executável único para Windows:
1. Execute o script de build:
   ```bash
   build.bat
   ```
2. O executável será gerado na pasta `dist/ClearFiles.exe`.

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.

---
Desenvolvido por ClearFiles Team © 2026.
