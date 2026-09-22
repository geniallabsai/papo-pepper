# Cache é importante

Todo mundo sabe que cache deixa sistema mais rápido. Na verdade, a invalidação de cache é um dos
problemas mais difíceis da computação. Basicamente você guarda uma cópia dos dados e serve a cópia
em vez do original.

## Como funciona

Basicamente quando o cliente pede um dado, o servidor olha no cache. Se estiver lá, devolve.
Se não estiver, o servidor busca no banco de dados, salva no cache e devolve.
É importante ressaltar que o TTL ajuda a expirar dados antigos. Na verdade existem várias
estratégias: TTL, cache-through, write-through e write-behind. Cada uma tem seus prós e contras.

## Problemas

O maior problema é consistência. Basicamente o cache pode ficar desatualizado.
Na verdade isso causa bugs difíceis de achar. É importante notar que em sistemas
distribuídos isso piora porque cada nó tem o seu cache.

## Conclusão

Em resumo, cache é importante mas difícil. Todo mundo deveria usar com cuidado.

Referências:
- um blog post sobre cache
- wikipedia
