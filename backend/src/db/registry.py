"""Registro de modelos ORM no Base.metadata.

Este módulo deve ser importado uma vez antes de qualquer operação que precise
do Base.metadata completo — migrações Alembic, create_all e similares.
A simples importação dos modelos é suficiente para registrá-los.
"""

# Módulo auth
import src.module.auth.model

# Módulo events
import src.module.events.model

# Módulo tickets
import src.module.tickets.model

# Módulo checkout
import src.module.checkout.model
