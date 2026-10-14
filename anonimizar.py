import hashlib
import os


# Usuarios genéricos del sistema y métodos de pago que no identifican a una persona
NO_PERSONALES = {
    'Administrador', 'Sin asignar', 'Buho PV', 'Caja PCD',
    'Efectivo Cafeteria', 'Otro PDC', 'Otros métodos', 'Otro',
}


def seudonimo(nombre: str, prefijo: str = 'Colaborador') -> str:
    """Reemplaza un nombre real por un código estable (mismo nombre -> mismo código en todos los reportes)."""
    if nombre in NO_PERSONALES:
        return nombre
    # Sal secreta (ANON_SALT en .env, nunca se sube) para que los códigos no se puedan revertir adivinando nombres
    sal = os.getenv('ANON_SALT', '')
    codigo = hashlib.sha256((sal + nombre.strip().lower()).encode('utf-8')).hexdigest()[:4].upper()
    return f"{prefijo} {codigo}"


PALABRAS_METODO = ('efectivo', 'tarjeta', 'transfer', 'otro', 'pdc', 'crédito', 'credito',
                   'débito', 'debito', 'vale', 'banco', 'cheque', 'cuenta')


def seudonimo_metodo(metodo: str) -> str:
    """Los métodos de pago con nombre de cajero (ej. 'Juan') se convierten en 'Caja XXXX'."""
    if any(p in metodo.lower() for p in PALABRAS_METODO):
        return metodo
    return seudonimo(metodo, prefijo='Caja')
