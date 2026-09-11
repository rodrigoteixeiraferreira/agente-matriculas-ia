-- ===============================================================
-- ESQUEMA DO BANCO
-- Rode este arquivo inteiro no SQL Editor do Supabase.
-- ===============================================================

create table cursos (
  id            bigserial primary key,
  nome          text not null,
  area          text not null,
  modalidade    text not null,
  duracao_meses int  not null,
  mensalidade   numeric(10,2) not null,
  descricao     text not null,
  ativo         boolean not null default true
);

create table turmas (
  id             bigserial primary key,
  curso_id       bigint not null references cursos(id),
  codigo         text not null unique,
  inicio         date not null,
  vagas_total    int  not null check (vagas_total > 0),
  inscricoes_ate date not null
);

create table inscricoes (
  id        bigserial primary key,
  turma_id  bigint not null references turmas(id),
  nome      text not null,
  email     text not null,
  telefone  text not null,
  criada_em timestamptz not null default now(),
  unique (turma_id, email)
);

create index idx_turmas_curso    on turmas(curso_id);
create index idx_inscricoes_turma on inscricoes(turma_id);

-- ---------------------------------------------------------------
-- Vagas disponiveis: SEMPRE calculado, nunca guardado em coluna.
-- ---------------------------------------------------------------
create or replace function vagas_disponiveis(p_turma_id bigint)
returns int
language sql
stable
as $$
  select t.vagas_total - count(i.id)::int
  from turmas t
  left join inscricoes i on i.turma_id = t.id
  where t.id = p_turma_id
  group by t.vagas_total;
$$;

-- ---------------------------------------------------------------
-- Cria a pre-inscricao de forma atomica, validando as regras.
-- ---------------------------------------------------------------
create or replace function criar_pre_inscricao(
  p_turma_id bigint,
  p_nome     text,
  p_email    text,
  p_telefone text
) returns json
language plpgsql
as $$
declare
  v_turma turmas%rowtype;
  v_vagas int;
  v_id    bigint;
begin
  select * into v_turma from turmas where id = p_turma_id for update;

  if not found then
    return json_build_object('ok', false, 'motivo', 'turma_inexistente');
  end if;

  if v_turma.inscricoes_ate < current_date then
    return json_build_object('ok', false, 'motivo', 'prazo_encerrado');
  end if;

  select vagas_disponiveis(p_turma_id) into v_vagas;

  if v_vagas <= 0 then
    return json_build_object('ok', false, 'motivo', 'sem_vagas');
  end if;

  insert into inscricoes (turma_id, nome, email, telefone)
  values (p_turma_id, p_nome, p_email, p_telefone)
  returning id into v_id;

  return json_build_object(
    'ok', true,
    'inscricao_id', v_id,
    'vagas_restantes', v_vagas - 1
  );
exception
  when unique_violation then
    return json_build_object('ok', false, 'motivo', 'ja_inscrito');
end;
$$;
