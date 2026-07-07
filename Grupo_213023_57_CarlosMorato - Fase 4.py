"""
================================================================================
SISTEMA INTEGRAL DE GESTIÓN DE CLIENTES, SERVICIOS Y RESERVAS
Empresa: Software FJ
================================================================================
Desarrollado por: Carlos Morato - Estudiante UNAD
Curso            : Programación - Código 213023
Fase             : 4 - Componente Práctico / Prácticas Simuladas
Ejercicio        : 1 - Sistema Integral de Gestión

Principios OOP implementados:
  - Abstracción    : EntidadBase y Servicio como clases abstractas (ABC)
  - Herencia       : ReservaSala, AlquilerEquipo, AsesoriaEspecializada
  - Polimorfismo   : calcular_costo() y describir() por tipo de servicio
  - Encapsulamiento: atributos privados con propiedades validadas en Cliente
  - Excepciones    : personalizadas, try/except/else/finally, encadenamiento

Archivo de logs: logs/sistema.log
Sin uso de base de datos: toda la persistencia es en memoria (listas de objetos)
================================================================================
"""

# ── Importaciones estándar ───────────────────────────────────────────────────
import os
import re
import uuid
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font as tkfont
from abc import ABC, abstractmethod
from datetime import datetime


# ================================================================================
# SECCIÓN 1: EXCEPCIONES PERSONALIZADAS
# Jerarquía propia del dominio Software FJ para manejo granular de errores.
# 20260607
# ================================================================================

class SistemaFJError(Exception):
    """
    Excepción base del sistema Software FJ.
    Todas las excepciones del dominio heredan de esta clase,
    lo que permite capturar cualquier error del sistema con un solo except.
    """
    def __init__(self, mensaje, codigo=None):
        super().__init__(mensaje)
        self.mensaje   = mensaje
        self.codigo    = codigo or "SFJ-000"
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __str__(self):
        return f"[{self.codigo}] {self.mensaje}"


# ── Excepciones de Cliente ────────────────────────────────────────────────────
class ClienteInvalidoError(SistemaFJError):
    """Error base para datos inválidos de cliente."""
    def __init__(self, mensaje):
        super().__init__(mensaje, "SFJ-100")

class NombreInvalidoError(ClienteInvalidoError):
    """El nombre del cliente está vacío o contiene caracteres no permitidos."""
    def __init__(self, nombre):
        super().__init__(
            f"Nombre inválido: '{nombre}'. Debe tener al menos 2 caracteres y solo letras.")
        self.codigo = "SFJ-101"

class EmailInvalidoError(ClienteInvalidoError):
    """El email no tiene formato válido (debe contener @ y dominio)."""
    def __init__(self, email):
        super().__init__(
            f"Email inválido: '{email}'. Formato esperado: usuario@dominio.com")
        self.codigo = "SFJ-102"

class TelefonoInvalidoError(ClienteInvalidoError):
    """El teléfono no tiene el formato numérico esperado."""
    def __init__(self, telefono):
        super().__init__(
            f"Teléfono inválido: '{telefono}'. Debe tener mínimo 7 dígitos numéricos.")
        self.codigo = "SFJ-103"


# ── Excepciones de Servicio ───────────────────────────────────────────────────
class ServicioError(SistemaFJError):
    """Error base para operaciones de servicio."""
    def __init__(self, mensaje):
        super().__init__(mensaje, "SFJ-200")

class ServicioNoDisponibleError(ServicioError):
    """El servicio solicitado no está disponible actualmente."""
    def __init__(self, nombre_servicio):
        super().__init__(
            f"El servicio '{nombre_servicio}' no está disponible en este momento.")
        self.codigo = "SFJ-201"

class ServicioNoEncontradoError(ServicioError):
    """No se encontró el servicio con el ID dado."""
    def __init__(self, servicio_id):
        super().__init__(
            f"Servicio con ID '{servicio_id}' no encontrado en el sistema.")
        self.codigo = "SFJ-202"

class PrecioInvalidoError(ServicioError):
    """El precio base del servicio no es válido."""
    def __init__(self, precio):
        super().__init__(
            f"Precio inválido: {precio}. El precio base debe ser mayor a cero.")
        self.codigo = "SFJ-203"

class CapacidadExcedidaError(ServicioError):
    """La cantidad de personas excede la capacidad máxima de la sala."""
    def __init__(self, solicitadas, maximas):
        super().__init__(
            f"Capacidad excedida: se solicitaron {solicitadas} personas "
            f"pero la sala tiene un máximo de {maximas}.")
        self.codigo    = "SFJ-204"
        self.solicitadas = solicitadas
        self.maximas     = maximas


# ── Excepciones de Reserva ────────────────────────────────────────────────────
class ReservaError(SistemaFJError):
    """Error base para operaciones de reserva."""
    def __init__(self, mensaje):
        super().__init__(mensaje, "SFJ-300")

class ReservaInvalidaError(ReservaError):
    """La reserva no cumple con las condiciones mínimas para procesarse."""
    def __init__(self, motivo):
        super().__init__(f"Reserva inválida: {motivo}")
        self.codigo = "SFJ-301"

class DuracionInvalidaError(ReservaError):
    """La duración de la reserva no es un valor positivo."""
    def __init__(self, duracion):
        super().__init__(
            f"Duración inválida: {duracion}. La duración debe ser mayor a cero.")
        self.codigo = "SFJ-302"

class EstadoInvalidoError(ReservaError):
    """La transición de estado de la reserva no está permitida."""
    def __init__(self, estado_actual, estado_nuevo):
        super().__init__(
            f"No se puede cambiar de '{estado_actual}' a '{estado_nuevo}'.")
        self.codigo = "SFJ-303"


# ================================================================================
# SECCIÓN 2: LOGGER DEL SISTEMA
# Registra todos los eventos y errores en un archivo de texto plano.
# Usa try/except/finally para garantizar que el archivo siempre se cierre.
# 20260706
# ================================================================================

class LoggerSistema:
    """
    Gestiona el registro de eventos y errores del sistema Software FJ.
    Escribe en logs/sistema.log con timestamp, nivel y mensaje.
    Implementa try/except/finally para manejo seguro del archivo.
    """

    NIVELES = {"INFO": "INFO ", "ERROR": "ERROR", "WARN": "WARN ", "DEBUG": "DEBUG"}

    def __init__(self, ruta_log="logs/sistema.log"):
        """
        Inicializa el logger creando el directorio y archivo si no existen.
        Args:
            ruta_log (str): Ruta relativa al archivo de log.
        """
        self._ruta = ruta_log
        self._crear_directorio()

    def _crear_directorio(self):
        """Crea el directorio de logs si no existe."""
        try:
            directorio = os.path.dirname(self._ruta)
            if directorio and not os.path.exists(directorio):
                os.makedirs(directorio)
        except OSError as e:
            # Encadenamiento de excepción: convierte OSError en error del dominio
            raise SistemaFJError(
                f"No se pudo crear el directorio de logs: {e}") from e

    def _escribir(self, nivel, mensaje):
        """
        Escribe una línea formateada en el archivo de log.
        Usa try/except/finally para garantizar el cierre del archivo.

        Args:
            nivel   (str): Nivel del log (INFO, ERROR, WARN, DEBUG).
            mensaje (str): Texto del evento a registrar.
        """
        archivo = None
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        etiqueta  = self.NIVELES.get(nivel, "INFO ")
        linea     = f"[{timestamp}] [{etiqueta}] {mensaje}\n"

        try:
            # try: intenta abrir y escribir en el archivo
            archivo = open(self._ruta, "a", encoding="utf-8")
            archivo.write(linea)
        except PermissionError as e:
            # except: error específico de permisos del sistema operativo
            print(f"[LOG-ERROR] Sin permisos para escribir en {self._ruta}: {e}")
        except OSError as e:
            # except: cualquier otro error de sistema de archivos
            print(f"[LOG-ERROR] Error de sistema al escribir log: {e}")
        finally:
            # finally: SIEMPRE cierra el archivo, ocurra o no un error
            if archivo:
                archivo.close()

    def info(self, mensaje):
        """Registra un evento informativo."""
        self._escribir("INFO", mensaje)

    def error(self, mensaje):
        """Registra un error del sistema."""
        self._escribir("ERROR", mensaje)

    def advertencia(self, mensaje):
        """Registra una advertencia."""
        self._escribir("WARN", mensaje)

    def debug(self, mensaje):
        """Registra información de depuración."""
        self._escribir("DEBUG", mensaje)

    def leer_ultimas(self, n=50):
        """
        Lee las últimas n líneas del archivo de log.
        Usa try/except/else/finally — patrón completo de manejo de excepciones.

        Args:
            n (int): Número de líneas a retornar.
        Returns:
            str: Las últimas n líneas del log.
        """
        archivo = None
        try:
            # try: intenta abrir el archivo en modo lectura
            archivo = open(self._ruta, "r", encoding="utf-8")
            lineas  = archivo.readlines()
        except FileNotFoundError:
            # except: el archivo no existe todavía
            return "El archivo de log aún no contiene registros."
        except OSError as e:
            # except: error de sistema de archivos
            return f"Error al leer el log: {e}"
        else:
            # else: solo se ejecuta si NO hubo excepción
            ultimas = lineas[-n:] if len(lineas) >= n else lineas
            return "".join(ultimas)
        finally:
            # finally: siempre cierra el archivo
            if archivo:
                archivo.close()


# ================================================================================
# SECCIÓN 3: CLASE ABSTRACTA BASE
# Define la interfaz común para todas las entidades del sistema.
# ================================================================================

class EntidadBase(ABC):
    """
    Clase abstracta base del sistema Software FJ.
    Implementa ABSTRACCIÓN: define la interfaz mínima que toda entidad
    del sistema debe cumplir, sin implementar los detalles concretos.

    Attributes:
        _id           (str): Identificador único auto-generado.
        _fecha_creacion(str): Timestamp de creación del objeto.
    """

    def __init__(self):
        """Genera automáticamente el ID único y registra la fecha de creación."""
        self._id            = str(uuid.uuid4())[:8].upper()
        self._fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def id(self):
        """Retorna el identificador único de la entidad (solo lectura)."""
        return self._id

    @property
    def fecha_creacion(self):
        """Retorna la fecha de creación de la entidad (solo lectura)."""
        return self._fecha_creacion

    @abstractmethod
    def mostrar_info(self):
        """
        Método abstracto: cada subclase debe implementar su propia
        representación informativa. ABSTRACCIÓN en acción.
        """
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self._id})"


# ================================================================================
# SECCIÓN 4: CLASE CLIENTE
# Implementa ENCAPSULAMIENTO con atributos privados y propiedades validadas.
# 20260706
# ================================================================================

class Cliente(EntidadBase):
    """
    Representa un cliente de Software FJ.
    Implementa ENCAPSULAMIENTO: los atributos son privados (_nombre, _email,
    _telefono) y solo se accede a ellos mediante propiedades con validación.
    Cada setter lanza excepciones personalizadas si el valor es inválido.

    Attributes:
        _nombre   (str): Nombre completo del cliente.
        _email    (str): Correo electrónico con formato válido.
        _telefono (str): Número telefónico con mínimo 7 dígitos.
        _activo   (bool): Estado del cliente en el sistema.
    """

    # Prefijo para IDs de cliente
    _PREFIJO = "CLI"
    _contador = 0

    def __init__(self, nombre: str, email: str, telefono: str):
        """
        Crea un nuevo cliente validando todos los datos de entrada.
        Usa try/except/else en cada validación para manejo granular de errores.

        Args:
            nombre   (str): Nombre completo del cliente.
            email    (str): Correo electrónico.
            telefono (str): Número telefónico.

        Raises:
            NombreInvalidoError  : Si el nombre está vacío o es inválido.
            EmailInvalidoError   : Si el email no tiene formato correcto.
            TelefonoInvalidoError: Si el teléfono no tiene suficientes dígitos.
        """
        super().__init__()
        Cliente._contador += 1
        self._id      = f"{self._PREFIJO}-{Cliente._contador:03d}"
        self._activo  = True

        # Las propiedades llaman a los setters que validan cada campo
        self.nombre   = nombre
        self.email    = email
        self.telefono = telefono

    # ── Propiedad: nombre ────────────────────────────────────────────────────
    @property
    def nombre(self):
        """Retorna el nombre del cliente."""
        return self._nombre

    @nombre.setter
    def nombre(self, valor):
        """
        Valida y establece el nombre del cliente.
        Raises:
            NombreInvalidoError: Si el nombre no cumple los requisitos mínimos.
        """
        valor = str(valor).strip() if valor else ""
        if not valor or len(valor) < 2:
            raise NombreInvalidoError(valor)
        # Solo permite letras, espacios, tildes y ñ
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$", valor):
            raise NombreInvalidoError(valor)
        self._nombre = valor

    # ── Propiedad: email ─────────────────────────────────────────────────────
    @property
    def email(self):
        """Retorna el email del cliente."""
        return self._email

    @email.setter
    def email(self, valor):
        """
        Valida y establece el email del cliente.
        Raises:
            EmailInvalidoError: Si el email no tiene formato user@domain.ext.
        """
        valor = str(valor).strip() if valor else ""
        patron = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
        if not re.match(patron, valor):
            raise EmailInvalidoError(valor)
        self._email = valor

    # ── Propiedad: telefono ──────────────────────────────────────────────────
    @property
    def telefono(self):
        """Retorna el teléfono del cliente."""
        return self._telefono

    @telefono.setter
    def telefono(self, valor):
        """
        Valida y establece el teléfono del cliente.
        Raises:
            TelefonoInvalidoError: Si el teléfono tiene menos de 7 dígitos.
        """
        valor = str(valor).strip() if valor else ""
        solo_digitos = re.sub(r"[\s\-\(\)\+]", "", valor)
        if not solo_digitos.isdigit() or len(solo_digitos) < 7:
            raise TelefonoInvalidoError(valor)
        self._telefono = valor

    @property
    def activo(self):
        """Retorna el estado activo/inactivo del cliente."""
        return self._activo

    def desactivar(self):
        """Marca el cliente como inactivo en el sistema."""
        self._activo = False

    def mostrar_info(self, mostrar_completo=False):
        """
        SOBRECARGA SIMULADA mediante parámetro opcional.
        - mostrar_completo=False → solo datos básicos
        - mostrar_completo=True  → todos los datos incluyendo estado y fecha

        Args:
            mostrar_completo (bool): Nivel de detalle de la información.
        Returns:
            str: Información formateada del cliente.
        """
        info = (
            f"ID: {self._id}\n"
            f"Nombre   : {self._nombre}\n"
            f"Email    : {self._email}\n"
            f"Teléfono : {self._telefono}\n"
        )
        if mostrar_completo:
            estado = "Activo" if self._activo else "Inactivo"
            info += (
                f"Estado   : {estado}\n"
                f"Registro : {self._fecha_creacion}\n"
            )
        return info

    def __str__(self):
        return f"Cliente({self._id} - {self._nombre})"


# ================================================================================
# SECCIÓN 5: CLASE ABSTRACTA SERVICIO Y SUBCLASES
# Implementa HERENCIA y POLIMORFISMO en la jerarquía de servicios.
# 20260706
# ================================================================================

class Servicio(EntidadBase, ABC):
    """
    Clase abstracta que define la interfaz común para todos los servicios
    de Software FJ. Implementa HERENCIA (hereda de EntidadBase) y
    ABSTRACCIÓN (métodos abstractos que cada servicio debe implementar).

    Los métodos calcular_costo() y describir() son polimórficos:
    el mismo nombre produce comportamientos distintos en cada subclase.

    Attributes:
        _nombre       (str)  : Nombre del servicio.
        _descripcion  (str)  : Descripción detallada.
        _precio_base  (float): Precio base sin impuestos ni descuentos.
        _disponible   (bool) : Disponibilidad actual del servicio.
    """

    _PREFIJO  = "SVC"
    _contador = 0

    def __init__(self, nombre: str, descripcion: str, precio_base: float):
        """
        Inicializa el servicio con validación del precio base.

        Args:
            nombre       (str)  : Nombre del servicio.
            descripcion  (str)  : Descripción del servicio.
            precio_base  (float): Tarifa base del servicio.

        Raises:
            PrecioInvalidoError: Si el precio es <= 0.
        """
        super().__init__()
        Servicio._contador += 1
        self._id          = f"{self._PREFIJO}-{Servicio._contador:03d}"
        self._nombre      = str(nombre).strip()
        self._descripcion = str(descripcion).strip()
        self._disponible  = True

        # Valida el precio base mediante try/except
        try:
            precio = float(precio_base)
            if precio <= 0:
                raise ValueError("Precio no positivo")
            self._precio_base = precio
        except (ValueError, TypeError) as e:
            # Encadenamiento: convierte el error genérico en error del dominio
            raise PrecioInvalidoError(precio_base) from e

    # ── Propiedades de solo lectura ──────────────────────────────────────────
    @property
    def nombre(self):
        return self._nombre

    @property
    def descripcion(self):
        return self._descripcion

    @property
    def precio_base(self):
        return self._precio_base

    @property
    def disponible(self):
        return self._disponible

    def activar(self):
        """Marca el servicio como disponible."""
        self._disponible = True

    def desactivar(self):
        """Marca el servicio como no disponible."""
        self._disponible = False

    def _aplicar_impuesto(self, costo, con_impuesto):
        """
        Aplica el IVA del 19% si se solicita.
        Método auxiliar compartido por todas las subclases.
        """
        return costo * 1.19 if con_impuesto else costo

    def _aplicar_descuento(self, costo, descuento):
        """
        Aplica el porcentaje de descuento indicado.
        Valida que el descuento esté entre 0 y 1 (0% a 100%).
        """
        try:
            d = float(descuento)
            if not (0 <= d <= 1):
                raise ValueError("Descuento fuera de rango")
            return costo * (1 - d)
        except (ValueError, TypeError):
            # Si el descuento es inválido, no aplica ninguno
            return costo

    @abstractmethod
    def calcular_costo(self, duracion, **kwargs):
        """
        POLIMORFISMO: cada servicio calcula su costo de manera diferente.
        SOBRECARGA SIMULADA: acepta parámetros opcionales vía **kwargs.
        """
        pass

    @abstractmethod
    def describir(self):
        """
        POLIMORFISMO: cada servicio provee su propia descripción detallada.
        """
        pass

    @abstractmethod
    def validar_parametros(self, **kwargs):
        """
        Valida los parámetros específicos de cada tipo de servicio
        antes de calcular el costo o crear una reserva.
        """
        pass

    def mostrar_info(self):
        """Información básica del servicio."""
        estado = "Disponible" if self._disponible else "No disponible"
        return (
            f"ID         : {self._id}\n"
            f"Nombre     : {self._nombre}\n"
            f"Descripción: {self._descripcion}\n"
            f"Precio base: ${self._precio_base:,.0f}/unidad\n"
            f"Estado     : {estado}\n"
        )

    def __str__(self):
        return f"{self.__class__.__name__}({self._id} - {self._nombre})"


# ── Subclase 1: ReservaSala ──────────────────────────────────────────────────
class ReservaSala(Servicio):
    """
    Servicio de reserva de sala de reuniones.
    HERENCIA: hereda de Servicio y sobrescribe los métodos abstractos.
    POLIMORFISMO: calcular_costo() considera capacidad y proyector.

    Attributes:
        _capacidad_maxima (int)  : Personas máximas que admite la sala.
        _tiene_proyector  (bool) : Si la sala cuenta con proyector.
        _piso             (int)  : Piso en el que se ubica la sala.
    """

    def __init__(self, nombre, descripcion, precio_hora,
                 capacidad_maxima, tiene_proyector=False, piso=1):
        super().__init__(nombre, descripcion, precio_hora)
        self._capacidad_maxima = int(capacidad_maxima)
        self._tiene_proyector  = bool(tiene_proyector)
        self._piso             = int(piso)

    @property
    def capacidad_maxima(self):
        return self._capacidad_maxima

    def validar_parametros(self, personas=1, **kwargs):
        """
        Valida que la cantidad de personas no exceda la capacidad.
        Raises:
            CapacidadExcedidaError: Si personas > capacidad_maxima.
        """
        try:
            p = int(personas)
            if p > self._capacidad_maxima:
                raise CapacidadExcedidaError(p, self._capacidad_maxima)
            if p <= 0:
                raise ReservaInvalidaError("La cantidad de personas debe ser mayor a cero.")
        except (ValueError, TypeError) as e:
            raise ReservaInvalidaError(f"Parámetro 'personas' inválido: {personas}") from e

    def calcular_costo(self, duracion, personas=1, descuento=0, con_impuesto=False, **kwargs):
        """
        POLIMORFISMO + SOBRECARGA SIMULADA:
        Costo = precio_hora * horas * (1 + recargo_proyector) * (1-descuento) * (1+IVA)

        Args:
            duracion     (float): Horas de reserva.
            personas     (int)  : Número de asistentes (solo para validar).
            descuento    (float): Porcentaje de descuento 0.0-1.0.
            con_impuesto (bool) : Aplicar IVA 19%.
        Returns:
            float: Costo total calculado.
        """
        if not self._disponible:
            raise ServicioNoDisponibleError(self._nombre)

        self.validar_parametros(personas=personas)

        # Recargo del 15% si la sala tiene proyector
        recargo = 1.15 if self._tiene_proyector else 1.0
        costo   = self._precio_base * float(duracion) * recargo
        costo   = self._aplicar_descuento(costo, descuento)
        costo   = self._aplicar_impuesto(costo, con_impuesto)
        return round(costo, 2)

    def describir(self):
        """POLIMORFISMO: descripción específica para salas."""
        proyector = "Con proyector" if self._tiene_proyector else "Sin proyector"
        return (
            f"[SALA] {self._nombre}\n"
            f"  Capacidad : {self._capacidad_maxima} personas\n"
            f"  Proyector : {proyector}\n"
            f"  Piso      : {self._piso}\n"
            f"  Tarifa    : ${self._precio_base:,.0f}/hora\n"
        )

    def mostrar_info(self):
        return super().mostrar_info() + (
            f"Tipo       : Reserva de Sala\n"
            f"Capacidad  : {self._capacidad_maxima} personas\n"
            f"Proyector  : {'Sí' if self._tiene_proyector else 'No'}\n"
            f"Piso       : {self._piso}\n"
        )


# ── Subclase 2: AlquilerEquipo ───────────────────────────────────────────────
class AlquilerEquipo(Servicio):
    """
    Servicio de alquiler de equipos tecnológicos.
    HERENCIA: hereda de Servicio. POLIMORFISMO: costo por días y cantidad.

    Attributes:
        _tipo_equipo         (str): Tipo de equipo (laptop, proyector, etc).
        _marca               (str): Marca del equipo.
        _cantidad_disponible (int): Unidades disponibles para alquilar.
    """

    def __init__(self, nombre, descripcion, precio_dia,
                 tipo_equipo, marca, cantidad_disponible=1):
        super().__init__(nombre, descripcion, precio_dia)
        self._tipo_equipo         = str(tipo_equipo)
        self._marca               = str(marca)
        self._cantidad_disponible = int(cantidad_disponible)

    @property
    def cantidad_disponible(self):
        return self._cantidad_disponible

    def validar_parametros(self, cantidad=1, **kwargs):
        """
        Valida que haya suficientes unidades disponibles.
        Raises:
            ServicioNoDisponibleError: Si no hay unidades disponibles.
            ReservaInvalidaError     : Si la cantidad solicitada es inválida.
        """
        try:
            c = int(cantidad)
            if c <= 0:
                raise ReservaInvalidaError("La cantidad de equipos debe ser mayor a cero.")
            if c > self._cantidad_disponible:
                raise ServicioNoDisponibleError(
                    f"{self._nombre} (solicitadas: {c}, disponibles: {self._cantidad_disponible})")
        except (ValueError, TypeError) as e:
            raise ReservaInvalidaError(f"Parámetro 'cantidad' inválido: {cantidad}") from e

    def calcular_costo(self, duracion, cantidad=1, descuento=0, con_impuesto=False, **kwargs):
        """
        POLIMORFISMO + SOBRECARGA SIMULADA:
        Costo = precio_dia * dias * cantidad * (1-descuento) * (1+IVA)

        Args:
            duracion     (float): Días de alquiler.
            cantidad     (int)  : Número de unidades a alquilar.
            descuento    (float): Porcentaje de descuento 0.0-1.0.
            con_impuesto (bool) : Aplicar IVA 19%.
        Returns:
            float: Costo total calculado.
        """
        if not self._disponible:
            raise ServicioNoDisponibleError(self._nombre)

        self.validar_parametros(cantidad=cantidad)

        costo = self._precio_base * float(duracion) * int(cantidad)
        costo = self._aplicar_descuento(costo, descuento)
        costo = self._aplicar_impuesto(costo, con_impuesto)
        return round(costo, 2)

    def describir(self):
        """POLIMORFISMO: descripción específica para equipos."""
        return (
            f"[EQUIPO] {self._nombre}\n"
            f"  Tipo      : {self._tipo_equipo}\n"
            f"  Marca     : {self._marca}\n"
            f"  Disponibles: {self._cantidad_disponible} unidad(es)\n"
            f"  Tarifa    : ${self._precio_base:,.0f}/día\n"
        )

    def mostrar_info(self):
        return super().mostrar_info() + (
            f"Tipo       : Alquiler de Equipo\n"
            f"Equipo     : {self._tipo_equipo} - {self._marca}\n"
            f"Disponibles: {self._cantidad_disponible}\n"
        )


# ── Subclase 3: AsesoriaEspecializada ────────────────────────────────────────
class AsesoriaEspecializada(Servicio):
    """
    Servicio de asesoría especializada en áreas de tecnología.
    HERENCIA: hereda de Servicio. POLIMORFISMO: costo ajustado por nivel.

    Attributes:
        _especialidad  (str): Área de la asesoría (Python, Oracle, Redes...).
        _nivel         (str): Nivel ofrecido (Básico, Intermedio, Avanzado).
        _nombre_asesor (str): Nombre del asesor asignado.
    """

    # Factor multiplicador según el nivel del cliente
    _FACTORES_NIVEL = {"Básico": 1.0, "Intermedio": 1.3, "Avanzado": 1.6}

    def __init__(self, nombre, descripcion, precio_hora,
                 especialidad, nivel, nombre_asesor):
        super().__init__(nombre, descripcion, precio_hora)
        self._especialidad  = str(especialidad)
        self._nivel         = str(nivel)
        self._nombre_asesor = str(nombre_asesor)

    def validar_parametros(self, nivel_cliente="Básico", **kwargs):
        """
        Valida que el nivel del cliente sea válido.
        Raises:
            ReservaInvalidaError: Si el nivel no está en los permitidos.
        """
        if nivel_cliente not in self._FACTORES_NIVEL:
            niveles_validos = ", ".join(self._FACTORES_NIVEL.keys())
            raise ReservaInvalidaError(
                f"Nivel '{nivel_cliente}' no válido. "
                f"Opciones permitidas: {niveles_validos}")

    def calcular_costo(self, duracion, nivel_cliente="Básico",
                       descuento=0, con_impuesto=False, **kwargs):
        """
        POLIMORFISMO + SOBRECARGA SIMULADA:
        Costo = precio_hora * horas * factor_nivel * (1-descuento) * (1+IVA)

        Args:
            duracion      (float): Horas de asesoría.
            nivel_cliente (str)  : Nivel del cliente (afecta la tarifa).
            descuento     (float): Porcentaje de descuento 0.0-1.0.
            con_impuesto  (bool) : Aplicar IVA 19%.
        Returns:
            float: Costo total calculado.
        """
        if not self._disponible:
            raise ServicioNoDisponibleError(self._nombre)

        self.validar_parametros(nivel_cliente=nivel_cliente)

        factor = self._FACTORES_NIVEL[nivel_cliente]
        costo  = self._precio_base * float(duracion) * factor
        costo  = self._aplicar_descuento(costo, descuento)
        costo  = self._aplicar_impuesto(costo, con_impuesto)
        return round(costo, 2)

    def describir(self):
        """POLIMORFISMO: descripción específica para asesorías."""
        return (
            f"[ASESORÍA] {self._nombre}\n"
            f"  Especialidad: {self._especialidad}\n"
            f"  Nivel       : {self._nivel}\n"
            f"  Asesor      : {self._nombre_asesor}\n"
            f"  Tarifa base : ${self._precio_base:,.0f}/hora\n"
        )

    def mostrar_info(self):
        return super().mostrar_info() + (
            f"Tipo       : Asesoría Especializada\n"
            f"Especialidad: {self._especialidad}\n"
            f"Nivel      : {self._nivel}\n"
            f"Asesor     : {self._nombre_asesor}\n"
        )


# ================================================================================
# SECCIÓN 6: CLASE RESERVA
# Integra cliente + servicio, gestiona estados y usa todos los patrones
# de manejo de excepciones requeridos.
# ================================================================================

class Reserva(EntidadBase):
    """
    Representa una reserva de servicio realizada por un cliente.
    Integra un Cliente y un Servicio, gestiona el ciclo de vida
    (PENDIENTE → CONFIRMADA → CANCELADA) y registra todo en el log.

    Attributes:
        _cliente         (Cliente) : Cliente que realiza la reserva.
        _servicio        (Servicio): Servicio reservado.
        _duracion        (float)   : Duración en la unidad del servicio.
        _estado          (str)     : Estado actual de la reserva.
        _costo_total     (float)   : Costo calculado al confirmar.
        _parametros_extra(dict)    : Parámetros adicionales para calcular_costo.
    """

    ESTADOS       = {"PENDIENTE", "CONFIRMADA", "CANCELADA"}
    _PREFIJO      = "RES"
    _contador     = 0

    # Transiciones de estado permitidas
    _TRANSICIONES = {
        "PENDIENTE" : {"CONFIRMADA", "CANCELADA"},
        "CONFIRMADA": {"CANCELADA"},
        "CANCELADA" : set()         # Estado terminal
    }

    def __init__(self, cliente: Cliente, servicio: Servicio,
                 duracion: float, **kwargs):
        """
        Crea una reserva en estado PENDIENTE.

        Args:
            cliente  (Cliente) : Objeto cliente válido.
            servicio (Servicio): Objeto servicio válido.
            duracion (float)   : Duración de la reserva (horas o días).
            **kwargs           : Parámetros extra para calcular_costo.

        Raises:
            ReservaInvalidaError : Si el cliente o servicio son inválidos.
            DuracionInvalidaError: Si la duración no es positiva.
        """
        super().__init__()
        Reserva._contador += 1
        self._id = f"{self._PREFIJO}-{Reserva._contador:03d}"

        # Valida el cliente
        if not isinstance(cliente, Cliente):
            raise ReservaInvalidaError("El cliente no es un objeto Cliente válido.")
        if not cliente.activo:
            raise ReservaInvalidaError(f"El cliente '{cliente.nombre}' está inactivo.")

        # Valida el servicio
        if not isinstance(servicio, Servicio):
            raise ReservaInvalidaError("El servicio no es un objeto Servicio válido.")

        # Valida la duración
        try:
            d = float(duracion)
            if d <= 0:
                raise DuracionInvalidaError(duracion)
            self._duracion = d
        except (ValueError, TypeError) as e:
            raise DuracionInvalidaError(duracion) from e

        self._cliente          = cliente
        self._servicio         = servicio
        self._estado           = "PENDIENTE"
        self._costo_total      = 0.0
        self._parametros_extra = kwargs

    @property
    def estado(self):
        return self._estado

    @property
    def costo_total(self):
        return self._costo_total

    @property
    def cliente(self):
        return self._cliente

    @property
    def servicio(self):
        return self._servicio

    def _cambiar_estado(self, nuevo_estado):
        """
        Gestiona las transiciones de estado válidas.
        Raises:
            EstadoInvalidoError: Si la transición no está permitida.
        """
        if nuevo_estado not in self._TRANSICIONES[self._estado]:
            raise EstadoInvalidoError(self._estado, nuevo_estado)
        self._estado = nuevo_estado

    def procesar(self, logger: LoggerSistema):
        """
        Procesa la reserva: valida parámetros, calcula costo y confirma.
        Usa el patrón try/except/else/finally COMPLETO — el más robusto.

        Args:
            logger (LoggerSistema): Logger del sistema para registrar eventos.

        Returns:
            float: Costo total calculado si el procesamiento fue exitoso.

        Raises:
            ServicioNoDisponibleError: Si el servicio no está disponible.
            SistemaFJError           : Cualquier otro error del dominio.
        """
        try:
            # try: intenta calcular el costo y validar el servicio
            if not self._servicio.disponible:
                raise ServicioNoDisponibleError(self._servicio.nombre)

            # POLIMORFISMO: calcular_costo() se comporta según el tipo de servicio
            self._costo_total = self._servicio.calcular_costo(
                self._duracion, **self._parametros_extra)

            self._cambiar_estado("CONFIRMADA")

        except ServicioNoDisponibleError as e:
            # except específico: servicio no disponible
            logger.error(f"Reserva {self._id} fallida: {e}")
            raise   # Re-lanza para que el llamador también lo maneje

        except (DuracionInvalidaError, CapacidadExcedidaError,
                ReservaInvalidaError) as e:
            # except agrupado: errores de parámetros
            logger.error(f"Reserva {self._id} - Parámetros inválidos: {e}")
            raise

        except SistemaFJError as e:
            # except genérico del dominio: captura cualquier otro error propio
            logger.error(f"Reserva {self._id} - Error del sistema: {e}")
            raise

        except Exception as e:
            # except genérico de Python: errores inesperados
            # Encadenamiento: convierte excepción genérica en error del dominio
            nuevo_error = ReservaInvalidaError(
                f"Error inesperado al procesar reserva: {e}")
            logger.error(str(nuevo_error))
            raise nuevo_error from e

        else:
            # else: SOLO se ejecuta si NO hubo ninguna excepción
            logger.info(
                f"Reserva {self._id} CONFIRMADA | "
                f"Cliente: {self._cliente.nombre} | "
                f"Servicio: {self._servicio.nombre} | "
                f"Duración: {self._duracion} | "
                f"Costo: ${self._costo_total:,.2f}")
            return self._costo_total

        finally:
            # finally: SIEMPRE se ejecuta, con o sin error
            logger.debug(
                f"Procesamiento de reserva {self._id} finalizado. "
                f"Estado: {self._estado}")

    def cancelar(self, logger: LoggerSistema):
        """
        Cancela la reserva si el estado lo permite.
        Usa try/except para manejar la transición de estado.

        Args:
            logger (LoggerSistema): Logger del sistema.
        """
        try:
            self._cambiar_estado("CANCELADA")
        except EstadoInvalidoError as e:
            logger.error(f"Cancelación de {self._id} rechazada: {e}")
            raise
        else:
            logger.advertencia(
                f"Reserva {self._id} CANCELADA | "
                f"Cliente: {self._cliente.nombre} | "
                f"Servicio: {self._servicio.nombre}")

    def mostrar_info(self):
        """Retorna la información completa de la reserva."""
        return (
            f"ID Reserva : {self._id}\n"
            f"Cliente    : {self._cliente.nombre} ({self._cliente.id})\n"
            f"Servicio   : {self._servicio.nombre} ({self._servicio.id})\n"
            f"Duración   : {self._duracion}\n"
            f"Estado     : {self._estado}\n"
            f"Costo Total: ${self._costo_total:,.2f}\n"
            f"Creada     : {self._fecha_creacion}\n"
        )

    def __str__(self):
        return (f"Reserva({self._id} | {self._cliente.nombre} → "
                f"{self._servicio.nombre} | {self._estado})")


# ================================================================================
# SECCIÓN 7: GESTOR PRINCIPAL — SistemaFJ
# Orquesta todas las operaciones y ejecuta las 10 simulaciones.
# ================================================================================

class SistemaFJ:
    """
    Motor central del Sistema Integral de Gestión Software FJ.
    Administra las listas internas de clientes, servicios y reservas.
    Provee las operaciones de negocio y ejecuta las simulaciones.
    No usa base de datos: toda la información vive en memoria.
    """

    def __init__(self):
        """Inicializa las listas vacías y el logger del sistema."""
        self._clientes  = []
        self._servicios = []
        self._reservas  = []
        self._logger    = LoggerSistema("logs/sistema.log")
        self._logger.info("=" * 60)
        self._logger.info("Sistema Software FJ iniciado correctamente.")
        self._logger.info("=" * 60)

    # ── Gestión de Clientes ──────────────────────────────────────────────────
    def registrar_cliente(self, nombre, email, telefono):
        """
        Registra un nuevo cliente con validación completa.
        Usa try/except/else/finally para demostrar el patrón completo.

        Returns:
            Cliente | None: El objeto cliente si el registro fue exitoso.
        """
        cliente = None
        try:
            # try: intenta crear el cliente (los setters validan)
            cliente = Cliente(nombre, email, telefono)
            self._clientes.append(cliente)

        except NombreInvalidoError as e:
            self._logger.error(f"Registro fallido - {e}")
            raise

        except EmailInvalidoError as e:
            self._logger.error(f"Registro fallido - {e}")
            raise

        except TelefonoInvalidoError as e:
            self._logger.error(f"Registro fallido - {e}")
            raise

        except ClienteInvalidoError as e:
            self._logger.error(f"Registro fallido (datos inválidos): {e}")
            raise

        else:
            # else: éxito — solo se ejecuta si no hubo excepción
            self._logger.info(
                f"Cliente registrado: {cliente.nombre} | "
                f"ID: {cliente.id} | Email: {cliente.email}")
            return cliente

        finally:
            # finally: siempre se ejecuta
            total = len(self._clientes)
            self._logger.debug(
                f"Total clientes en sistema: {total}")

    def buscar_cliente(self, cliente_id):
        """Busca un cliente por ID. Retorna None si no existe."""
        for c in self._clientes:
            if c.id == cliente_id:
                return c
        return None

    # ── Gestión de Servicios ─────────────────────────────────────────────────
    def agregar_servicio(self, servicio):
        """
        Agrega un servicio al catálogo del sistema.

        Args:
            servicio (Servicio): Instancia de cualquier subclase de Servicio.
        """
        try:
            if not isinstance(servicio, Servicio):
                raise ServicioError("El objeto proporcionado no es un Servicio válido.")
            self._servicios.append(servicio)
        except ServicioError as e:
            self._logger.error(f"Error al agregar servicio: {e}")
            raise
        else:
            self._logger.info(
                f"Servicio agregado: {servicio.nombre} | "
                f"ID: {servicio.id} | Tipo: {type(servicio).__name__}")

    def buscar_servicio(self, servicio_id):
        """
        Busca un servicio por ID.
        Raises:
            ServicioNoEncontradoError: Si no existe el servicio.
        """
        for s in self._servicios:
            if s.id == servicio_id:
                return s
        raise ServicioNoEncontradoError(servicio_id)

    # ── Gestión de Reservas ──────────────────────────────────────────────────
    def crear_reserva(self, cliente, servicio, duracion, **kwargs):
        """
        Crea y procesa una nueva reserva.

        Args:
            cliente  (Cliente) : Cliente que reserva.
            servicio (Servicio): Servicio a reservar.
            duracion (float)   : Duración de la reserva.
            **kwargs           : Parámetros adicionales del servicio.

        Returns:
            Reserva | None: La reserva confirmada o None si falla.
        """
        try:
            reserva = Reserva(cliente, servicio, duracion, **kwargs)
            reserva.procesar(self._logger)
            self._reservas.append(reserva)
            return reserva

        except (DuracionInvalidaError, ReservaInvalidaError,
                ServicioNoDisponibleError, CapacidadExcedidaError) as e:
            self._logger.advertencia(
                f"Reserva no creada para {cliente.nombre}: {e}")
            raise

        except SistemaFJError as e:
            self._logger.error(f"Error inesperado en reserva: {e}")
            raise

    def cancelar_reserva(self, reserva_id):
        """
        Cancela una reserva existente por su ID.

        Returns:
            bool: True si se canceló correctamente.
        """
        for r in self._reservas:
            if r.id == reserva_id:
                try:
                    r.cancelar(self._logger)
                    return True
                except EstadoInvalidoError as e:
                    self._logger.error(str(e))
                    raise
        self._logger.advertencia(f"Reserva {reserva_id} no encontrada para cancelar.")
        return False

    # ── Reportes ─────────────────────────────────────────────────────────────
    def calcular_total_reservas(self):
        """
        POLIMORFISMO en acción: itera la lista mixta de reservas
        y suma los costos sin importar el tipo de servicio.

        Returns:
            dict: Resumen con total, confirmadas y canceladas.
        """
        total       = 0.0
        confirmadas = 0
        canceladas  = 0

        # Un solo ciclo — polimorfismo maneja el tipo internamente
        for reserva in self._reservas:
            if reserva.estado == "CONFIRMADA":
                total      += reserva.costo_total
                confirmadas += 1
            elif reserva.estado == "CANCELADA":
                canceladas += 1

        return {
            "total_ingresos": total,
            "confirmadas"   : confirmadas,
            "canceladas"    : canceladas,
            "total_reservas": len(self._reservas),
            "clientes"      : len(self._clientes),
            "servicios"     : len(self._servicios)
        }

    # ── 10 Simulaciones ───────────────────────────────────────────────────────
    def ejecutar_simulaciones(self, callback=None):
        """
        Ejecuta las 10 simulaciones requeridas por el Anexo 3.
        Cada simulación registra su resultado en el log.
        El callback permite actualizar la interfaz gráfica en tiempo real.

        Args:
            callback (callable): Función para mostrar resultados en la GUI.
        """

        def log_y_mostrar(tipo, mensaje):
            """Helper local para registrar y mostrar simultáneamente."""
            if tipo == "OK":
                self._logger.info(f"[SIM] {mensaje}")
                prefijo = "✅"
            elif tipo == "ERROR":
                self._logger.error(f"[SIM] {mensaje}")
                prefijo = "❌"
            else:
                self._logger.advertencia(f"[SIM] {mensaje}")
                prefijo = "⚠️"

            linea = f"{prefijo} {mensaje}"
            if callback:
                callback(linea)
            return linea

        resultados = []
        self._logger.info("=" * 60)
        self._logger.info("INICIO DE SIMULACIONES — Sistema Software FJ")
        self._logger.info("=" * 60)

        # ── CONFIGURACIÓN: servicios para las simulaciones ────────────────
        sala_orion  = ReservaSala(
            "Sala Orión", "Sala de juntas premium piso 3",
            80000, capacidad_maxima=10, tiene_proyector=True, piso=3)
        laptop_dell = AlquilerEquipo(
            "Laptop Dell XPS", "Laptop i7 16GB RAM",
            45000, "Laptop", "Dell", cantidad_disponible=3)
        asesoria_py = AsesoriaEspecializada(
            "Asesoría Python", "Capacitación en Python OOP",
            120000, "Python", "Intermedio", "Ing. García")
        equipo_off  = AlquilerEquipo(
            "Cámara Sony", "Cámara 4K para eventos",
            60000, "Cámara", "Sony", cantidad_disponible=1)

        for s in [sala_orion, laptop_dell, asesoria_py, equipo_off]:
            self.agregar_servicio(s)

        # Marca el último equipo como no disponible para la simulación 7
        equipo_off.desactivar()

        # ─────────────────────────────────────────────────────────────────
        # SIMULACIÓN 1: Registro de cliente válido
        # ─────────────────────────────────────────────────────────────────
        resultados.append(log_y_mostrar("", "─" * 50))
        resultados.append(log_y_mostrar("", "SIMULACIÓN 1: Registrar cliente válido"))
        try:
            c1 = self.registrar_cliente("Ana Torres", "ana.torres@gmail.com", "3001234567")
        except SistemaFJError as e:
            resultados.append(log_y_mostrar("ERROR", str(e)))
        else:
            resultados.append(
                log_y_mostrar("OK", f"Cliente registrado: {c1.nombre} | ID: {c1.id}"))

        # ─────────────────────────────────────────────────────────────────
        # SIMULACIÓN 2: Cliente con email inválido (sin @)
        # ─────────────────────────────────────────────────────────────────
        resultados.append(log_y_mostrar("", "─" * 50))
        resultados.append(log_y_mostrar("", "SIMULACIÓN 2: Email inválido"))
        try:
            self.registrar_cliente("Luis Pérez", "correoSinArroba", "3109876543")
        except EmailInvalidoError as e:
            resultados.append(log_y_mostrar("ERROR", f"Capturado correctamente → {e}"))
        except SistemaFJError as e:
            resultados.append(log_y_mostrar("ERROR", str(e)))

        # ─────────────────────────────────────────────────────────────────
        # SIMULACIÓN 3: Cliente con nombre vacío
        # ─────────────────────────────────────────────────────────────────
        resultados.append(log_y_mostrar("", "─" * 50))
        resultados.append(log_y_mostrar("", "SIMULACIÓN 3: Nombre vacío"))
        try:
            self.registrar_cliente("", "valido@correo.com", "3201112233")
        except NombreInvalidoError as e:
            resultados.append(log_y_mostrar("ERROR", f"Capturado correctamente → {e}"))
        except SistemaFJError as e:
            resultados.append(log_y_mostrar("ERROR", str(e)))

        # ─────────────────────────────────────────────────────────────────
        # SIMULACIÓN 4: Reserva de sala exitosa
        # ─────────────────────────────────────────────────────────────────
        resultados.append(log_y_mostrar("", "─" * 50))
        resultados.append(log_y_mostrar("", "SIMULACIÓN 4: Reservar sala exitosamente"))
        c2 = None
        r1 = None
        try:
            c2 = self.registrar_cliente(
                "María Gómez", "maria.gomez@empresa.co", "6017654321")
            r1 = self.crear_reserva(
                c2, sala_orion, 3,
                personas=5, descuento=0.1, con_impuesto=True)
        except SistemaFJError as e:
            resultados.append(log_y_mostrar("ERROR", str(e)))
        else:
            resultados.append(log_y_mostrar(
                "OK",
                f"Reserva {r1.id} confirmada | "
                f"Costo: ${r1.costo_total:,.2f}"))

        # ─────────────────────────────────────────────────────────────────
        # SIMULACIÓN 5: Capacidad excedida en sala
        # ─────────────────────────────────────────────────────────────────
        resultados.append(log_y_mostrar("", "─" * 50))
        resultados.append(log_y_mostrar("", "SIMULACIÓN 5: Capacidad excedida en sala"))
        try:
            if c2:
                self.crear_reserva(
                    c2, sala_orion, 2,
                    personas=50)  # Supera el límite de 10
        except CapacidadExcedidaError as e:
            resultados.append(log_y_mostrar("ERROR", f"Capturado correctamente → {e}"))
        except SistemaFJError as e:
            resultados.append(log_y_mostrar("ERROR", str(e)))

        # ─────────────────────────────────────────────────────────────────
        # SIMULACIÓN 6: Alquiler de equipo exitoso
        # ─────────────────────────────────────────────────────────────────
        resultados.append(log_y_mostrar("", "─" * 50))
        resultados.append(log_y_mostrar("", "SIMULACIÓN 6: Alquiler de equipo exitoso"))
        c3 = None
        r2 = None
        try:
            c3 = self.registrar_cliente(
                "Pedro Ramírez", "pedro.r@tech.org", "3154449900")
            r2 = self.crear_reserva(
                c3, laptop_dell, 5,
                cantidad=2, con_impuesto=False)
        except SistemaFJError as e:
            resultados.append(log_y_mostrar("ERROR", str(e)))
        else:
            resultados.append(log_y_mostrar(
                "OK",
                f"Alquiler {r2.id} confirmado | "
                f"Costo: ${r2.costo_total:,.2f}"))

        # ─────────────────────────────────────────────────────────────────
        # SIMULACIÓN 7: Equipo marcado como no disponible
        # ─────────────────────────────────────────────────────────────────
        resultados.append(log_y_mostrar("", "─" * 50))
        resultados.append(log_y_mostrar("", "SIMULACIÓN 7: Equipo no disponible"))
        try:
            if c3:
                self.crear_reserva(c3, equipo_off, 2)
        except ServicioNoDisponibleError as e:
            resultados.append(log_y_mostrar("ERROR", f"Capturado correctamente → {e}"))
        except SistemaFJError as e:
            resultados.append(log_y_mostrar("ERROR", str(e)))

        # ─────────────────────────────────────────────────────────────────
        # SIMULACIÓN 8: Asesoría especializada confirmada con descuento
        # ─────────────────────────────────────────────────────────────────
        resultados.append(log_y_mostrar("", "─" * 50))
        resultados.append(log_y_mostrar("", "SIMULACIÓN 8: Asesoría confirmada con descuento"))
        r3 = None
        try:
            if c1:
                r3 = self.crear_reserva(
                    c1, asesoria_py, 4,
                    nivel_cliente="Avanzado",
                    descuento=0.15,
                    con_impuesto=True)
        except SistemaFJError as e:
            resultados.append(log_y_mostrar("ERROR", str(e)))
        else:
            resultados.append(log_y_mostrar(
                "OK",
                f"Asesoría {r3.id} confirmada | "
                f"Costo: ${r3.costo_total:,.2f}"))

        # ─────────────────────────────────────────────────────────────────
        # SIMULACIÓN 9: Reserva con duración negativa
        # ─────────────────────────────────────────────────────────────────
        resultados.append(log_y_mostrar("", "─" * 50))
        resultados.append(log_y_mostrar("", "SIMULACIÓN 9: Duración negativa"))
        try:
            if c1:
                self.crear_reserva(c1, sala_orion, -2)
        except DuracionInvalidaError as e:
            resultados.append(log_y_mostrar("ERROR", f"Capturado correctamente → {e}"))
        except SistemaFJError as e:
            resultados.append(log_y_mostrar("ERROR", str(e)))

        # ─────────────────────────────────────────────────────────────────
        # SIMULACIÓN 10: Cancelar reserva y generar reporte
        # ─────────────────────────────────────────────────────────────────
        resultados.append(log_y_mostrar("", "─" * 50))
        resultados.append(log_y_mostrar("", "SIMULACIÓN 10: Cancelar reserva y reporte"))
        try:
            if r1:
                self.cancelar_reserva(r1.id)
                resultados.append(log_y_mostrar(
                    "OK", f"Reserva {r1.id} cancelada correctamente."))
        except SistemaFJError as e:
            resultados.append(log_y_mostrar("ERROR", str(e)))

        # Reporte final
        reporte = self.calcular_total_reservas()
        resumen = (
            f"\n{'='*50}\n"
            f"  REPORTE FINAL DEL SISTEMA\n"
            f"{'='*50}\n"
            f"  Clientes registrados : {reporte['clientes']}\n"
            f"  Servicios activos    : {reporte['servicios']}\n"
            f"  Reservas totales     : {reporte['total_reservas']}\n"
            f"  Confirmadas          : {reporte['confirmadas']}\n"
            f"  Canceladas           : {reporte['canceladas']}\n"
            f"  Total ingresos       : ${reporte['total_ingresos']:,.2f}\n"
            f"{'='*50}"
        )
        self._logger.info(resumen)
        resultados.append(resumen if not callback else callback(resumen))

        self._logger.info("=" * 60)
        self._logger.info("FIN DE SIMULACIONES")
        self._logger.info("=" * 60)

        return resultados

    # ── Getters para la interfaz ─────────────────────────────────────────────
    @property
    def clientes(self):
        return self._clientes.copy()

    @property
    def servicios(self):
        return self._servicios.copy()

    @property
    def reservas(self):
        return self._reservas.copy()

    @property
    def logger(self):
        return self._logger


# ================================================================================
# SECCIÓN 8: INTERFAZ GRÁFICA — Tkinter
# Interfaz en inglés con 5 pestañas funcionales.
# ================================================================================

class SoftwareFJApp(tk.Tk):
    """
    Interfaz gráfica principal del Sistema Software FJ.
    Implementada con Tkinter, completamente en inglés.
    Conecta la capa de presentación con el motor SistemaFJ.
    """

    # ── Paleta de colores ────────────────────────────────────────────────────
    C_BG      = "#0D1B2A"
    C_PANEL   = "#1B2838"
    C_CARD    = "#243447"
    C_ACCENT  = "#00BFA5"
    C_ACCENT2 = "#448AFF"
    C_WARN    = "#FF5252"
    C_GOLD    = "#FFD740"
    C_TEXT    = "#E8F0FE"
    C_MUTED   = "#90A4AE"
    C_BORDER  = "#2D4059"
    C_GREEN   = "#69F0AE"

    def __init__(self):
        super().__init__()
        self.title("Software FJ — Integrated Management System  |  UNAD 213023")
        self.geometry("1150x780")
        self.minsize(950, 680)
        self.configure(bg=self.C_BG)
        self.resizable(True, True)

        # Inicializa el motor del sistema
        self.sistema = SistemaFJ()

        # Guard para status bar (patrón ya corregido en Fase 3)
        self.lbl_status = None
        self.lbl_count  = None

        self._definir_fuentes()
        self._build_header()
        self._build_notebook()
        self._build_status_bar()
        self._actualizar_status("System ready. Welcome to Software FJ.")

    def _definir_fuentes(self):
        self.fnt_title = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self.fnt_head  = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.fnt_body  = tkfont.Font(family="Segoe UI", size=10)
        self.fnt_small = tkfont.Font(family="Segoe UI", size=9)
        self.fnt_mono  = tkfont.Font(family="Consolas",  size=10)

    # ── Header ───────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=self.C_PANEL, height=65)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)

        tk.Frame(hdr, bg=self.C_ACCENT, width=5).pack(side=tk.LEFT, fill=tk.Y)

        inner = tk.Frame(hdr, bg=self.C_PANEL)
        inner.pack(side=tk.LEFT, padx=16, pady=8)

        tk.Label(inner, text="🏢  Software FJ — Client, Service & Reservation Management",
                 font=self.fnt_title, fg=self.C_TEXT,
                 bg=self.C_PANEL).pack(anchor="w")
        tk.Label(inner,
                 text="OOP Phase 4  ·  Abstraction · Inheritance · Polymorphism "
                      "· Encapsulation · Exception Handling",
                 font=self.fnt_small, fg=self.C_MUTED,
                 bg=self.C_PANEL).pack(anchor="w")

        now = datetime.now().strftime("%B %d, %Y")
        tk.Label(hdr, text=now, font=self.fnt_small,
                 fg=self.C_MUTED, bg=self.C_PANEL).pack(side=tk.RIGHT, padx=16)

    # ── Notebook ─────────────────────────────────────────────────────────────
    def _build_notebook(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("FJ.TNotebook",
                         background=self.C_BG, borderwidth=0)
        style.configure("FJ.TNotebook.Tab",
                         background=self.C_PANEL, foreground=self.C_MUTED,
                         padding=[16, 8], font=("Segoe UI", 10))
        style.map("FJ.TNotebook.Tab",
                  background=[("selected", self.C_CARD)],
                  foreground=[("selected", self.C_ACCENT)])

        self.nb = ttk.Notebook(self, style="FJ.TNotebook")
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=(6, 0))

        # ── Tab 1: Clients ────────────────────────────────────────────────
        t1 = tk.Frame(self.nb, bg=self.C_BG)
        self.nb.add(t1, text="  👤  Clients  ")
        self._build_tab_clients(t1)

        # ── Tab 2: Services ───────────────────────────────────────────────
        t2 = tk.Frame(self.nb, bg=self.C_BG)
        self.nb.add(t2, text="  🛠  Services  ")
        self._build_tab_services(t2)

        # ── Tab 3: Reservations ───────────────────────────────────────────
        t3 = tk.Frame(self.nb, bg=self.C_BG)
        self.nb.add(t3, text="  📋  Reservations  ")
        self._build_tab_reservations(t3)

        # ── Tab 4: Simulations ────────────────────────────────────────────
        t4 = tk.Frame(self.nb, bg=self.C_BG)
        self.nb.add(t4, text="  🧪  Simulations  ")
        self._build_tab_simulations(t4)

        # ── Tab 5: Reports ────────────────────────────────────────────────
        t5 = tk.Frame(self.nb, bg=self.C_BG)
        self.nb.add(t5, text="  📊  Reports & Logs  ")
        self._build_tab_reports(t5)

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1 — CLIENTS
    # ─────────────────────────────────────────────────────────────────────────
    def _build_tab_clients(self, parent):
        # Formulario
        form = tk.LabelFrame(parent, text="  Register New Client  ",
                              bg=self.C_CARD, fg=self.C_ACCENT,
                              font=self.fnt_head, bd=1)
        form.pack(fill=tk.X, padx=14, pady=10)

        self.cli_entries = {}
        fields = [("Full Name", "name"), ("Email", "email"), ("Phone", "phone")]
        for i, (label, key) in enumerate(fields):
            tk.Label(form, text=label + ":", font=self.fnt_body,
                     fg=self.C_MUTED, bg=self.C_CARD,
                     width=12, anchor="e").grid(row=i, column=0, padx=10, pady=6, sticky="e")
            e = tk.Entry(form, font=self.fnt_body,
                         bg="#1A2A3A", fg=self.C_TEXT,
                         insertbackground=self.C_ACCENT,
                         relief=tk.FLAT, bd=5, width=35)
            e.grid(row=i, column=1, padx=8, pady=6, sticky="w")
            self.cli_entries[key] = e

        btn_row = tk.Frame(form, bg=self.C_CARD)
        btn_row.grid(row=3, column=0, columnspan=2, pady=10)

        tk.Button(btn_row, text="  ✅  Register Client  ",
                  font=self.fnt_body,
                  bg=self.C_ACCENT, fg=self.C_BG,
                  relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                  command=self._registrar_cliente_gui).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_row, text="  🔄  Clear  ",
                  font=self.fnt_body,
                  bg=self.C_CARD, fg=self.C_TEXT,
                  relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                  command=lambda: [e.delete(0, tk.END)
                                   for e in self.cli_entries.values()]).pack(
                      side=tk.LEFT, padx=6)

        # Tabla
        tk.Label(parent, text="Registered Clients", font=self.fnt_head,
                 fg=self.C_TEXT, bg=self.C_BG).pack(anchor="w", padx=14)

        cols = ("ID", "Name", "Email", "Phone", "Status")
        self.tree_clients = self._make_tree(parent, cols, {
            "ID": 90, "Name": 200, "Email": 220, "Phone": 130, "Status": 90})

    def _registrar_cliente_gui(self):
        nombre   = self.cli_entries["name"].get().strip()
        email    = self.cli_entries["email"].get().strip()
        telefono = self.cli_entries["phone"].get().strip()
        try:
            c = self.sistema.registrar_cliente(nombre, email, telefono)
            self.tree_clients.insert("", tk.END,
                values=(c.id, c.nombre, c.email, c.telefono, "Active"))
            for e in self.cli_entries.values():
                e.delete(0, tk.END)
            self._actualizar_status(
                f"✅ Client '{c.nombre}' registered successfully.")
            messagebox.showinfo("Success",
                                f"Client '{c.nombre}' added.\nID: {c.id}")
        except SistemaFJError as e:
            self._actualizar_status(f"❌ {e}")
            messagebox.showerror("Registration Error", str(e))

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2 — SERVICES
    # ─────────────────────────────────────────────────────────────────────────
    def _build_tab_services(self, parent):
        top = tk.Frame(parent, bg=self.C_BG)
        top.pack(fill=tk.X, padx=14, pady=8)

        tk.Label(top, text="Service Type:", font=self.fnt_body,
                 fg=self.C_TEXT, bg=self.C_BG).pack(side=tk.LEFT)

        self.var_svc_tipo = tk.StringVar(value="Room")
        for t in ["Room", "Equipment", "Advisory"]:
            tk.Radiobutton(top, text=t, variable=self.var_svc_tipo, value=t,
                           font=self.fnt_body,
                           fg=self.C_TEXT, bg=self.C_BG,
                           selectcolor=self.C_CARD,
                           activebackground=self.C_BG,
                           command=self._toggle_svc_fields).pack(
                               side=tk.LEFT, padx=12)

        form = tk.LabelFrame(parent, text="  Service Details  ",
                              bg=self.C_CARD, fg=self.C_GOLD,
                              font=self.fnt_head, bd=1)
        form.pack(fill=tk.X, padx=14, pady=4)

        self.svc_entries = {}
        base_fields = [
            ("Name",        "svc_name"),
            ("Description", "svc_desc"),
            ("Base Price ($)", "svc_price"),
        ]
        for i, (label, key) in enumerate(base_fields):
            tk.Label(form, text=label + ":", font=self.fnt_body,
                     fg=self.C_MUTED, bg=self.C_CARD,
                     width=16, anchor="e").grid(row=i, column=0, padx=8, pady=5, sticky="e")
            e = tk.Entry(form, font=self.fnt_body,
                         bg="#1A2A3A", fg=self.C_TEXT,
                         insertbackground=self.C_GOLD,
                         relief=tk.FLAT, bd=5, width=30)
            e.grid(row=i, column=1, padx=6, pady=5, sticky="w")
            self.svc_entries[key] = e

        self.svc_extra_frame = tk.Frame(form, bg=self.C_CARD)
        self.svc_extra_frame.grid(row=3, column=0, columnspan=2, sticky="ew")
        self._toggle_svc_fields()

        tk.Button(form, text="  ➕  Add Service  ",
                  font=self.fnt_body,
                  bg=self.C_GOLD, fg=self.C_BG,
                  relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                  command=self._agregar_servicio_gui).grid(
                      row=4, column=0, columnspan=2, pady=10)

        tk.Label(parent, text="Available Services", font=self.fnt_head,
                 fg=self.C_TEXT, bg=self.C_BG).pack(anchor="w", padx=14)

        cols = ("ID", "Name", "Type", "Base Price", "Status")
        self.tree_svc = self._make_tree(parent, cols, {
            "ID": 90, "Name": 200, "Type": 160, "Base Price": 130, "Status": 110})

    def _toggle_svc_fields(self):
        for w in self.svc_extra_frame.winfo_children():
            w.destroy()
        self.svc_extra = {}

        tipo = self.var_svc_tipo.get()
        if tipo == "Room":
            extra = [("Max Capacity", "cap"), ("Has Projector (1/0)", "proj"), ("Floor", "floor")]
        elif tipo == "Equipment":
            extra = [("Equipment Type", "eq_type"), ("Brand", "brand"), ("Units Available", "qty")]
        else:
            extra = [("Specialty", "spec"), ("Level", "level"), ("Advisor Name", "advisor")]

        for i, (label, key) in enumerate(extra):
            tk.Label(self.svc_extra_frame, text=label + ":",
                     font=self.fnt_body, fg=self.C_MUTED,
                     bg=self.C_CARD, width=16, anchor="e").grid(
                         row=i, column=0, padx=8, pady=4, sticky="e")
            e = tk.Entry(self.svc_extra_frame, font=self.fnt_body,
                         bg="#1A2A3A", fg=self.C_TEXT,
                         insertbackground=self.C_GOLD,
                         relief=tk.FLAT, bd=5, width=25)
            e.grid(row=i, column=1, padx=6, pady=4, sticky="w")
            self.svc_extra[key] = e

    def _agregar_servicio_gui(self):
        try:
            nombre = self.svc_entries["svc_name"].get().strip()
            desc   = self.svc_entries["svc_desc"].get().strip()
            precio = float(self.svc_entries["svc_price"].get())
            tipo   = self.var_svc_tipo.get()

            if tipo == "Room":
                svc = ReservaSala(
                    nombre, desc, precio,
                    capacidad_maxima=int(self.svc_extra["cap"].get()),
                    tiene_proyector=bool(int(self.svc_extra["proj"].get() or 0)),
                    piso=int(self.svc_extra["floor"].get() or 1))
            elif tipo == "Equipment":
                svc = AlquilerEquipo(
                    nombre, desc, precio,
                    tipo_equipo=self.svc_extra["eq_type"].get(),
                    marca=self.svc_extra["brand"].get(),
                    cantidad_disponible=int(self.svc_extra["qty"].get() or 1))
            else:
                svc = AsesoriaEspecializada(
                    nombre, desc, precio,
                    especialidad=self.svc_extra["spec"].get(),
                    nivel=self.svc_extra["level"].get(),
                    nombre_asesor=self.svc_extra["advisor"].get())

            self.sistema.agregar_servicio(svc)
            self.tree_svc.insert("", tk.END,
                values=(svc.id, svc.nombre, tipo,
                        f"${svc.precio_base:,.0f}", "Available"))
            self._actualizar_status(f"✅ Service '{svc.nombre}' added.")
            messagebox.showinfo("Success", f"Service '{svc.nombre}' added.\nID: {svc.id}")

        except (ValueError, SistemaFJError) as e:
            messagebox.showerror("Service Error", str(e))
            self._actualizar_status(f"❌ {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 3 — RESERVATIONS
    # ─────────────────────────────────────────────────────────────────────────
    def _build_tab_reservations(self, parent):
        form = tk.LabelFrame(parent, text="  Create Reservation  ",
                              bg=self.C_CARD, fg=self.C_ACCENT2,
                              font=self.fnt_head, bd=1)
        form.pack(fill=tk.X, padx=14, pady=10)

        self.res_entries = {}
        fields = [
            ("Client ID",  "cli_id"),
            ("Service ID", "svc_id"),
            ("Duration",   "dur"),
            ("Persons/Units", "extra1"),
            ("Discount (0-1)", "discount"),
        ]
        for i, (label, key) in enumerate(fields):
            tk.Label(form, text=label + ":", font=self.fnt_body,
                     fg=self.C_MUTED, bg=self.C_CARD,
                     width=16, anchor="e").grid(row=i, column=0, padx=8, pady=5, sticky="e")
            e = tk.Entry(form, font=self.fnt_body,
                         bg="#1A2A3A", fg=self.C_TEXT,
                         insertbackground=self.C_ACCENT2,
                         relief=tk.FLAT, bd=5, width=25)
            e.grid(row=i, column=1, padx=6, pady=5, sticky="w")
            self.res_entries[key] = e

        self.var_iva = tk.BooleanVar()
        tk.Checkbutton(form, text="Apply Tax (19% IVA)",
                       variable=self.var_iva,
                       font=self.fnt_body,
                       fg=self.C_TEXT, bg=self.C_CARD,
                       selectcolor=self.C_PANEL,
                       activebackground=self.C_CARD).grid(
                           row=5, column=1, pady=4, sticky="w")

        btn_row = tk.Frame(form, bg=self.C_CARD)
        btn_row.grid(row=6, column=0, columnspan=2, pady=10)
        tk.Button(btn_row, text="  📋  Create & Confirm  ",
                  font=self.fnt_body,
                  bg=self.C_ACCENT2, fg="white",
                  relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                  command=self._crear_reserva_gui).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_row, text="  ❌  Cancel Selected  ",
                  font=self.fnt_body,
                  bg=self.C_WARN, fg="white",
                  relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                  command=self._cancelar_reserva_gui).pack(side=tk.LEFT, padx=6)

        tk.Label(parent, text="All Reservations", font=self.fnt_head,
                 fg=self.C_TEXT, bg=self.C_BG).pack(anchor="w", padx=14)

        cols = ("ID", "Client", "Service", "Duration", "Status", "Total Cost")
        self.tree_res = self._make_tree(parent, cols, {
            "ID": 90, "Client": 160, "Service": 180,
            "Duration": 80, "Status": 110, "Total Cost": 120})

    def _crear_reserva_gui(self):
        try:
            cli_id   = self.res_entries["cli_id"].get().strip()
            svc_id   = self.res_entries["svc_id"].get().strip()
            dur      = float(self.res_entries["dur"].get())
            extra1   = self.res_entries["extra1"].get().strip()
            discount = float(self.res_entries["discount"].get() or 0)
            con_iva  = self.var_iva.get()

            cliente  = self.sistema.buscar_cliente(cli_id)
            if not cliente:
                raise ReservaInvalidaError(f"Client ID '{cli_id}' not found.")

            servicio = self.sistema.buscar_servicio(svc_id)
            kwargs   = {"descuento": discount, "con_impuesto": con_iva}

            if isinstance(servicio, ReservaSala) and extra1:
                kwargs["personas"] = int(extra1)
            elif isinstance(servicio, AlquilerEquipo) and extra1:
                kwargs["cantidad"] = int(extra1)

            r = self.sistema.crear_reserva(cliente, servicio, dur, **kwargs)
            self.tree_res.insert("", tk.END, iid=r.id,
                values=(r.id, cliente.nombre, servicio.nombre,
                        dur, r.estado, f"${r.costo_total:,.2f}"))
            self._actualizar_status(
                f"✅ Reservation {r.id} confirmed | Cost: ${r.costo_total:,.2f}")
            messagebox.showinfo("Confirmed",
                                f"Reservation {r.id} confirmed!\n"
                                f"Total cost: ${r.costo_total:,.2f}")

        except SistemaFJError as e:
            messagebox.showerror("Reservation Error", str(e))
            self._actualizar_status(f"❌ {e}")
        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid numeric value: {e}")

    def _cancelar_reserva_gui(self):
        sel = self.tree_res.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a reservation to cancel.")
            return
        res_id = sel[0]
        if messagebox.askyesno("Confirm", f"Cancel reservation {res_id}?"):
            try:
                self.sistema.cancelar_reserva(res_id)
                self.tree_res.set(res_id, "Status", "CANCELLED")
                self._actualizar_status(f"⚠️ Reservation {res_id} cancelled.")
            except SistemaFJError as e:
                messagebox.showerror("Error", str(e))

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 4 — SIMULATIONS
    # ─────────────────────────────────────────────────────────────────────────
    def _build_tab_simulations(self, parent):
        bar = tk.Frame(parent, bg=self.C_BG, pady=10)
        bar.pack(fill=tk.X, padx=14)

        tk.Label(bar,
                 text="Automated System Simulations (10 operations — valid & invalid)",
                 font=self.fnt_head, fg=self.C_TEXT,
                 bg=self.C_BG).pack(side=tk.LEFT)

        tk.Button(bar, text="  🚀  Run All Simulations  ",
                  font=self.fnt_body,
                  bg=self.C_GREEN, fg=self.C_BG,
                  relief=tk.FLAT, padx=16, pady=6, cursor="hand2",
                  command=self._ejecutar_simulaciones).pack(side=tk.RIGHT)

        frame_txt = tk.Frame(parent, bg=self.C_BG)
        frame_txt.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 8))

        self.txt_sim = scrolledtext.ScrolledText(
            frame_txt,
            font=self.fnt_mono,
            bg=self.C_CARD, fg=self.C_GREEN,
            insertbackground=self.C_ACCENT,
            relief=tk.FLAT, bd=6,
            state=tk.DISABLED, wrap=tk.WORD)
        self.txt_sim.pack(fill=tk.BOTH, expand=True)

    def _ejecutar_simulaciones(self):
        self.txt_sim.config(state=tk.NORMAL)
        self.txt_sim.delete("1.0", tk.END)
        self.txt_sim.insert(tk.END,
            "Running simulations... Please wait.\n"
            "=" * 55 + "\n\n")
        self.txt_sim.config(state=tk.DISABLED)
        self.update()

        def mostrar(linea):
            self.txt_sim.config(state=tk.NORMAL)
            self.txt_sim.insert(tk.END, str(linea) + "\n")
            self.txt_sim.see(tk.END)
            self.txt_sim.config(state=tk.DISABLED)
            self.update()

        try:
            self.sistema.ejecutar_simulaciones(callback=mostrar)
            self._actualizar_status(
                "✅ All 10 simulations completed. Check logs tab for details.")

            # Refresca las tablas de clientes y servicios
            self._refrescar_tablas_post_sim()

        except Exception as e:
            mostrar(f"\n❌ Unexpected error during simulations: {e}")
            self._actualizar_status(f"❌ Simulation error: {e}")

    def _refrescar_tablas_post_sim(self):
        """Actualiza las tablas de clients y services tras las simulaciones."""
        for row in self.tree_clients.get_children():
            self.tree_clients.delete(row)
        for c in self.sistema.clientes:
            estado = "Active" if c.activo else "Inactive"
            self.tree_clients.insert("", tk.END,
                values=(c.id, c.nombre, c.email, c.telefono, estado))

        for row in self.tree_svc.get_children():
            self.tree_svc.delete(row)
        for s in self.sistema.servicios:
            tipo   = type(s).__name__
            estado = "Available" if s.disponible else "Unavailable"
            self.tree_svc.insert("", tk.END,
                values=(s.id, s.nombre, tipo,
                        f"${s.precio_base:,.0f}", estado))

        for row in self.tree_res.get_children():
            self.tree_res.delete(row)
        for r in self.sistema.reservas:
            self.tree_res.insert("", tk.END, iid=r.id,
                values=(r.id, r.cliente.nombre, r.servicio.nombre,
                        r.servicio._precio_base,
                        r.estado, f"${r.costo_total:,.2f}"))

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 5 — REPORTS & LOGS
    # ─────────────────────────────────────────────────────────────────────────
    def _build_tab_reports(self, parent):
        top = tk.Frame(parent, bg=self.C_BG, pady=8)
        top.pack(fill=tk.X, padx=14)
        tk.Label(top, text="System Report & Event Log",
                 font=self.fnt_head, fg=self.C_TEXT,
                 bg=self.C_BG).pack(side=tk.LEFT)

        tk.Button(top, text="  📊  Generate Report  ",
                  font=self.fnt_small,
                  bg=self.C_ACCENT, fg=self.C_BG,
                  relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
                  command=self._generar_reporte).pack(side=tk.RIGHT, padx=4)
        tk.Button(top, text="  📄  Refresh Log  ",
                  font=self.fnt_small,
                  bg=self.C_CARD, fg=self.C_TEXT,
                  relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
                  command=self._refrescar_log).pack(side=tk.RIGHT, padx=4)

        # Reporte
        rpt_frame = tk.LabelFrame(parent, text="  Summary Report  ",
                                   bg=self.C_CARD, fg=self.C_ACCENT,
                                   font=self.fnt_head, bd=1, height=160)
        rpt_frame.pack(fill=tk.X, padx=14, pady=4)
        rpt_frame.pack_propagate(False)

        self.txt_report = scrolledtext.ScrolledText(
            rpt_frame, font=self.fnt_mono,
            bg=self.C_CARD, fg=self.C_GOLD,
            relief=tk.FLAT, bd=4,
            state=tk.DISABLED, height=7)
        self.txt_report.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Log
        log_frame = tk.LabelFrame(parent, text="  Event Log (logs/sistema.log)  ",
                                   bg=self.C_CARD, fg=self.C_MUTED,
                                   font=self.fnt_head, bd=1)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=4)

        self.txt_log = scrolledtext.ScrolledText(
            log_frame, font=self.fnt_mono,
            bg="#0A1520", fg="#80CBC4",
            relief=tk.FLAT, bd=4,
            state=tk.DISABLED, height=14)
        self.txt_log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _generar_reporte(self):
        reporte = self.sistema.calcular_total_reservas()
        now = datetime.now().strftime("%B %d, %Y  %H:%M:%S")
        txt = (
            f"  Generated: {now}\n"
            f"  {'─'*44}\n"
            f"  Registered Clients  : {reporte['clientes']}\n"
            f"  Available Services  : {reporte['servicios']}\n"
            f"  Total Reservations  : {reporte['total_reservas']}\n"
            f"  Confirmed           : {reporte['confirmadas']}\n"
            f"  Cancelled           : {reporte['canceladas']}\n"
            f"  {'─'*44}\n"
            f"  Total Revenue       : ${reporte['total_ingresos']:>14,.2f}\n"
        )
        self.txt_report.config(state=tk.NORMAL)
        self.txt_report.delete("1.0", tk.END)
        self.txt_report.insert("1.0", txt)
        self.txt_report.config(state=tk.DISABLED)
        self._refrescar_log()
        self._actualizar_status(
            f"Report generated — Revenue: ${reporte['total_ingresos']:,.2f}")

    def _refrescar_log(self):
        contenido = self.sistema.logger.leer_ultimas(80)
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.delete("1.0", tk.END)
        self.txt_log.insert("1.0", contenido)
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    # ── Status Bar ────────────────────────────────────────────────────────────
    def _build_status_bar(self):
        bar = tk.Frame(self, bg=self.C_PANEL, height=26)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        self.lbl_status = tk.Label(bar, text="",
                                    font=self.fnt_small,
                                    fg=self.C_MUTED, bg=self.C_PANEL)
        self.lbl_status.pack(side=tk.LEFT, padx=12)

        self.lbl_count = tk.Label(bar, text="",
                                   font=self.fnt_small,
                                   fg=self.C_ACCENT, bg=self.C_PANEL)
        self.lbl_count.pack(side=tk.RIGHT, padx=12)

    def _actualizar_status(self, msg):
        """Guard check: los labels pueden ser None durante la construcción."""
        if self.lbl_status is None or self.lbl_count is None:
            return
        self.lbl_status.config(text=msg)
        r = self.sistema.calcular_total_reservas()
        self.lbl_count.config(
            text=f"Clients: {r['clientes']}  |  "
                 f"Reservations: {r['total_reservas']}  |  "
                 f"Revenue: ${r['total_ingresos']:,.2f}")

    # ── Utilidad: construir Treeview ──────────────────────────────────────────
    def _make_tree(self, parent, cols, widths):
        style = ttk.Style()
        style.configure("FJ.Treeview",
                         background=self.C_CARD,
                         foreground=self.C_TEXT,
                         fieldbackground=self.C_CARD,
                         rowheight=28,
                         font=("Segoe UI", 10))
        style.configure("FJ.Treeview.Heading",
                         background=self.C_PANEL,
                         foreground=self.C_ACCENT,
                         font=("Segoe UI", 10, "bold"),
                         relief="flat")
        style.map("FJ.Treeview",
                  background=[("selected", self.C_ACCENT2)],
                  foreground=[("selected", "white")])

        frame = tk.Frame(parent, bg=self.C_BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=(2, 8))

        tree = ttk.Treeview(frame, columns=cols, show="headings",
                             style="FJ.Treeview", selectmode="browse")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=widths.get(col, 120), anchor="center")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)
        return tree


# ================================================================================
# PUNTO DE ENTRADA
# ================================================================================
if __name__ == "__main__":
    app = SoftwareFJApp()
    app.mainloop()