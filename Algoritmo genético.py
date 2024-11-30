import pandas as pd
import random
#Clase maquina
class Maquina:
    def __init__(self, id, etapa, productos_rates):
        self.id = id
        self.etapa = etapa
        self.productos_rates = productos_rates
        self.disponible_desde = 0
        self.horario = []
        self.ultimo_producto = 999  # Usado para rastrear el último producto procesado

    def procesar_pedido(self, pedido, tiempo_inicio_etapa_anterior=0):
        rate = self.productos_rates.get(pedido.producto, 1)  # Rate predeterminado a 1
        setup = 0.3  # Tiempo de setup por defecto para todas las etapas excepto la 2

        if self.ultimo_producto != 999 and self.ultimo_producto != pedido.producto:
            if self.etapa == 2:
                setup = 0.5  # Tiempo de setup específico para la etapa 2

            # Calcular el tiempo de inicio incluyendo el tiempo de setup
            inicio_hora = max(self.disponible_desde % 16, tiempo_inicio_etapa_anterior % 16)
            inicio_dia = max(self.disponible_desde // 16, tiempo_inicio_etapa_anterior // 16)

            fin_hora = inicio_hora + setup
            fin_dia = inicio_dia

            while fin_hora >= 16:
                fin_hora -= 16
                fin_dia += 1

            if fin_dia > inicio_dia:
                inicio_dia = fin_dia
                inicio_hora = 0
                fin_hora = setup

            while fin_hora >= 16:
                fin_hora -= 16
                fin_dia += 1

            self.disponible_desde = fin_dia * 16 + fin_hora
            self.horario.append(("Set Up", inicio_dia, inicio_hora, fin_dia, fin_hora))

        # Procesar el pedido después de setup
        duracion = pedido.demanda / rate
        inicio_hora = max(self.disponible_desde % 16, tiempo_inicio_etapa_anterior % 16)
        inicio_dia = max(self.disponible_desde // 16, tiempo_inicio_etapa_anterior // 16)
        fin_hora = inicio_hora + duracion
        fin_dia = inicio_dia

        while fin_hora >= 16:
            fin_hora -= 16
            fin_dia += 1

        if fin_dia > inicio_dia:
            inicio_dia = fin_dia
            inicio_hora = 0
            fin_hora = duracion

        while fin_hora >= 16:
            fin_hora -= 16
            fin_dia += 1

        self.disponible_desde = fin_dia * 16 + fin_hora
        self.horario.append((pedido.id, inicio_dia, inicio_hora, fin_dia, fin_hora))
        self.ultimo_producto = pedido.producto

        return self.disponible_desde


#clase pedido
class Pedido:
    def __init__(self, id, demanda, fecha, producto):
        self.id = id
        self.demanda = demanda
        self.fecha = fecha
        self.producto = producto
        

#leer las maquinas desde csv
def crear_maquinas_desde_csv(filepath):
    data = pd.read_csv(filepath)
    maquinas = {}
    
    # Definir la etapa basada en el IdMaquina
    def asignar_etapa(id_maquina):
        if id_maquina <= 2:
            return 1
        elif id_maquina <= 4:
            return 2
        elif id_maquina <= 7:
            return 3
        else:
            return 1  # Default si hay más máquinas
    
    # Agrupar por IdMaquina y construir el diccionario de productos_rates para cada máquina
    for _, group in data.groupby('IdMaquina'):
        id_maquina = group['IdMaquina'].iloc[0]
        productos_rates = {row['IdProducto']: row['Rate'] for index, row in group.iterrows()}
        etapa = asignar_etapa(id_maquina)
        maquinas[id_maquina] = Maquina(id=id_maquina, etapa=etapa, productos_rates=productos_rates)
    
    return list(maquinas.values())

# crear pedidos desde csv
def crear_pedidos_desde_csv(filepath):
    data = pd.read_csv(filepath)
    pedidos = []
    
    for index, row in data.iterrows():
        id_pedido = row['IdExperimento']  # Usar IdExperimento como el ID del pedido
        demanda = row['Cantidad']
        fecha_limite = row[' Fecha Limite']
        id_producto = row[' IdProducto']
        
        # Crear una instancia de Pedido
        pedido = Pedido(id=id_pedido, demanda=demanda, fecha=fecha_limite, producto=id_producto)
        pedidos.append(pedido)
    
    return pedidos


# funcion fitness
def calcular_eficiencia(maquinas, pedidos):
    total_pedidos = len(pedidos)
    pedidos_a_tiempo = 0
    finales_pedidos = {pedido.id: 0 for pedido in pedidos}
    for maquina in maquinas:
        for pedido_id, inicio_dia, _, fin_dia, _ in maquina.horario:
            if pedido_id != 'Set Up':
                if fin_dia > finales_pedidos[pedido_id]:
                    finales_pedidos[pedido_id] = fin_dia
    for pedido in pedidos:
        if finales_pedidos[pedido.id] <= pedido.fecha:
            pedidos_a_tiempo += 1
    eficiencia = (pedidos_a_tiempo / total_pedidos) * 100 if total_pedidos > 0 else 0
    return eficiencia

def fitness(cromosoma, maquinas, pedidos):
    # Agrupar máquinas por etapa
    maquinas_por_etapa = {etapa: [] for etapa in set(m.etapa for m in maquinas)}
    for m in maquinas:
        m.horario.clear()
        m.disponible_desde = 0
        maquinas_por_etapa[m.etapa].append(m)

    # Registrar el tiempo final de cada pedido por etapa
    finales_por_pedido_etapa = {pedido.id: {etapa: 0 for etapa in maquinas_por_etapa} for pedido in pedidos}

    for id_pedido in cromosoma:
        pedido = next(p for p in pedidos if p.id == id_pedido)
        tiempo_inicio_etapa_anterior = 0

        for etapa in range(1, max(m.etapa for m in maquinas) + 1):
            if etapa in maquinas_por_etapa:
                # Encontrar la máquina más disponible en esta etapa
                maquina = min(maquinas_por_etapa[etapa], key=lambda m: m.disponible_desde)
                
                # Ajustar el tiempo de inicio de acuerdo al primer tiempo disponible
                if etapa > 1:  # Si no es la primera etapa
                    tiempo_inicio_etapa_anterior = max(
                        maquina.disponible_desde,
                        finales_por_pedido_etapa[pedido.id][etapa - 1]
                    )
                else:  # Primera etapa, solo considerar la disponibilidad de la máquina
                    tiempo_inicio_etapa_anterior = maquina.disponible_desde

                # Procesar el pedido en la máquina seleccionada
                fin_hora_total = maquina.procesar_pedido(pedido, tiempo_inicio_etapa_anterior)
                finales_por_pedido_etapa[pedido.id][etapa] = fin_hora_total

    return calcular_eficiencia(maquinas, pedidos)



# Ejemplo de uso
pedidos_creados = crear_pedidos_desde_csv('/Users/iguacio/Downloads/RATESyPedidos/PEDIDOS3.csv')
maquinas_creadas = crear_maquinas_desde_csv('/Users/iguacio/Downloads/RATESyPedidos/RATES3.csv')


def inicializar_poblacion(tamano_poblacion, num_pedidos):
    return [random.sample(range(num_pedidos), num_pedidos) for _ in range(tamano_poblacion)]

def calcular_fitness(poblacion, maquinas, pedidos):
    return [fitness(cromosoma, maquinas, pedidos) for cromosoma in poblacion]

def seleccionar(poblacion, fitnesses, num_seleccionados):
    seleccionados = sorted(zip(poblacion, fitnesses), key=lambda x: x[1], reverse=True)
    return [individuo for individuo, _ in seleccionados[:num_seleccionados]]

def cruzar(padre, madre):
    punto = random.randint(1, len(padre) - 1)
    hijo1 = padre[:punto] + [x for x in madre if x not in padre[:punto]]
    hijo2 = madre[:punto] + [x for x in padre if x not in madre[:punto]]
    return hijo1, hijo2

def mutar(cromosoma, probabilidad):
    if random.random() < probabilidad:
        i, j = random.sample(range(len(cromosoma)), 2)
        cromosoma[i], cromosoma[j] = cromosoma[j], cromosoma[i]
    return cromosoma

def algoritmo_genetico(maquinas, pedidos, tamano_poblacion=50, num_generaciones=200, prob_mutacion=0.1):
    poblacion = inicializar_poblacion(tamano_poblacion, len(pedidos))
    for generacion in range(num_generaciones):
        fit = calcular_fitness(poblacion, maquinas, pedidos)
        seleccionados = seleccionar(poblacion, fit, tamano_poblacion // 2)
        nueva_poblacion = seleccionados[:]
        while len(nueva_poblacion) < tamano_poblacion:
            padre, madre = random.sample(seleccionados, 2)
            hijo1, hijo2 = cruzar(padre, madre)
            nueva_poblacion.extend([mutar(hijo1, prob_mutacion), mutar(hijo2, prob_mutacion)])
        poblacion = nueva_poblacion
        print(f"Generación {generacion}: Mejor fitness = {max(fit)}")
    return poblacion[0]

# Ejemplo de uso
mejor_cromosoma = algoritmo_genetico(maquinas_creadas, pedidos_creados)
print("Mejor secuencia de pedidos:", mejor_cromosoma)

eficiencia = fitness(mejor_cromosoma, maquinas_creadas, pedidos_creados)
print(f"Eficiencia del cromosoma evaluado: {eficiencia}%")
# Imprimir los horarios de cada máquina

for maquina in maquinas_creadas:
    print(f"Máquina {maquina.id} - Etapa {maquina.etapa} - Horario:")
    for registro in maquina.horario:
        pedido_id, inicio_dia, inicio_hora, fin_dia, fin_hora = registro
        print(f"  Pedido {pedido_id}: Inicia Día {inicio_dia}, Hora {inicio_hora} - Finaliza Día {fin_dia}, Hora {fin_hora}")
    print("")  # Añade una línea en blanco para separar las máquinas visualmente
