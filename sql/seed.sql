-- ===============================================================
-- DADOS DE EXEMPLO
-- Rode DEPOIS do schema.sql.
--
-- Os valores nao sao aleatorios:
--   - a turma de IA tem 2 vagas  -> da para esgotar ao vivo na demo
--   - a de Marketing ja venceu   -> demonstra a regra de prazo
-- ===============================================================

insert into cursos (nome, area, modalidade, duracao_meses, mensalidade, descricao) values
('Pos-graduacao em Gestao de Negocios',        'Gestao',     'online',     12, 390.00, 'Formacao em gestao empresarial, financas e lideranca de equipes.'),
('Pos-graduacao em Inteligencia Artificial Aplicada', 'Tecnologia', 'hibrido', 12, 490.00, 'IA aplicada a processos e produtos digitais, com projeto pratico.'),
('Pos-graduacao em Psicologia Organizacional', 'Saude',      'presencial', 18, 450.00, 'Comportamento humano, clima e saude mental no ambiente de trabalho.'),
('Extensao em Marketing Digital',              'Marketing',  'online',      6, 250.00, 'Trafego pago, funil de conversao e mensuracao de campanhas.');

insert into turmas (curso_id, codigo, inicio, vagas_total, inscricoes_ate) values
(1, 'GN-2026-2', '2026-10-05', 40, '2026-09-25'),
(2, 'IA-2026-2', '2026-10-05',  2, '2026-09-30'),
(3, 'PO-2026-2', '2026-11-03', 25, '2026-10-20'),
(4, 'MD-2026-1', '2026-09-15', 30, '2026-09-05');
