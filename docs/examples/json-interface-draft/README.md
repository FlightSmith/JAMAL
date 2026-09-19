# Exemplos propostos de interface JSON

Estes arquivos acompanham [os requisitos do refactor](<C:/Users/User/Documents/ChatGPT/JAMAL 2/docs/REQUISITOS-REFACTOR-PYTHON.md>). São exemplos de estrutura para revisão, não inputs homologados nem uma implementação do schema.

- `polar-0002.json`: sweep de α, geração de malha e sequência 0, positivos, reload de 0, negativos.
- `polar-0003.json`: herda malha e solução de α=0°, β=0° da 0002, reutiliza esse ponto sem iterar e calcula β=1°…15°.

Os campos e enums são propostas. `assets/*` e o perfil numérico precisam ser fornecidos; os parâmetros de meshing são ilustrativos. O template numerado usado por essas polares na matriz não foi entregue, portanto estes arquivos não pretendem reproduzi-lo. Os dummies da estrutura de referência não servem para executar ANSA/Fluent.

`components: []` significa somente ADF total; arrays vazios em controles/propulsão significam que esses modos estão inativos. Uma seleção de simetria por papel pode resultar em conjunto vazio; farfield, paredes e fluido exigem grupos válidos. A regra final de validação pertence ao futuro schema.

No modo `from_source_solution`, os assets e a identidade de malha vêm do manifesto da origem, enquanto os valores de engenharia e as condições do destino continuam explícitos. `same_run` deve ser resolvido para uma execução concreta, sem procurar automaticamente a execução mais recente.

Os exemplos pedem 31 pontos calculados e 33000 iterações na 0002; na 0003,
15 pontos calculados e 15000 iterações, além do ponto reutilizado sem novas
iterações. São contagens do plano ilustrativo, não resultados de execução.

A sintaxe JSON e a coerência dos dois exemplos foram verificadas documentalmente. Nenhuma geração de malha, submissão ou execução CFD foi realizada.
