-- Migrar cards arquivados para a nova coluna 'archived'
-- (Se houver cards com archived=true, movê-los para column_id='archived')

UPDATE cards
SET column_id = 'archived'
WHERE archived = true;

-- Opcional: Remover coluna 'archived' após migração (se quiser limpar)
-- ALTER TABLE cards DROP COLUMN archived;
