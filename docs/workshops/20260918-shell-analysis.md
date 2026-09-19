# Análise do legado — 18/09/2026

Registro complementar, preservando os workshops anteriores.

O responsável mudou a estratégia de levantamento: usar o código entregue
em JAMAL_shell e a estrutura JAMAL_Struct_Folders como evidência para
documentar os requisitos de uma substituição completa em Python. A
interface frontend/backend continua sendo JSON, com prioridade para
legibilidade humana. Os arquivos de geometria, batch e malha indicados
são dummies.

Foi realizada análise estática de código, templates, matriz, imagem,
meshlog e fixtures. Nenhuma ferramenta CFD ou submissão foi executada.

## Resposta confirmada

Pergunta: quando a POLAR 003 parte do ponto α=0°, β=0° da POLAR 002,
deve reutilizar o resultado sem novas iterações ou recalcular esse ponto?

Resposta do responsável: **reutilizar o ponto salvo, sem novas iterações**.

Consequência: a 003 possui 16 pontos de resultado, dos quais β=1°…15°
são calculados e β=0° é reutilizado. A regra de executar todas as
iterações aplica-se aos pontos efetivamente calculados. Esta confirmação
foi promovida à emenda da ADR-0008, FR-033 e SPECS §6.2.

## Documento produzido

[Requisitos para o refactor completo em Python](<C:/Users/User/Documents/ChatGPT/JAMAL 2/docs/REQUISITOS-REFACTOR-PYTHON.md>)
descreve fluxo e dependências, 64 requisitos propostos, 20 cenários de
aceite, arquitetura e contratos propostos, limites do script ANSA retido,
ADF, problemas que não devem ser copiados e decisões pendentes.

Dois exemplos JSON ilustram as polares 0002 e 0003. São propostas de
interface, não schema aprovado ou arquivos prontos para executar no HPC.

## Conflitos destacados para revisão

- Definição de altitude e aplicação do desvio ISA: shell e rascunhos
  anteriores expressam convenções diferentes, ainda sem referência física
  homologada nesta análise.
- Metadados de malha: os requisitos anteriores proíbem log scraping, mas
  o script ANSA retido entrega informações no meshlog. O produtor de
  metadados estruturados precisa ser escolhido.
- Tipos, limites e posições das operações ANSA precisam refletir a
  capacidade do script retido, sem truncamento silencioso.
- Paridade de modos, contrato ADF, integração PBS e entradas reais
  precisam de homologação específica.

Esses pontos não foram convertidos em decisões aceitas automaticamente.
