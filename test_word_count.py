# -*- coding: utf-8 -*-
# Test word count of revised responses
topics_test = [
    {
        "id": "1.1",
        "prompt": "Un taller metalmecánico en Durán adquiere una soldadora MIG para unir estructuras 15% más rápido. Con base en el Manual de Oslo (OECD) y Cuervo et al., argumenta técnicamente por qué esto es una reposición de capital y no una innovación de proceso. Queda prohibido apelar a marketing digital o redes sociales: define los parámetros de ingeniería de métodos (tiempos de ciclo, balance de línea y rediseño de flujo de valor) que el taller debería transformar para constituir una verdadera innovación industrial.",
        "sample": "Según el Manual de Oslo y Cuervo et al., la simple compra de una soldadora más rápida es una reposición o modernización de bienes de capital que no altera la arquitectura productiva de la planta. Para constituir una innovación de proceso en la industria metalmecánica de Durán, la empresa debe transformar la ingeniería del flujo de valor: estandarizar tiempos mediante estudio de métodos (MTM), eliminar cuellos de botella en el ensamble, rediseñar las celdas de trabajo con balanceo de línea bajo manufactura esbelta e implementar control estadístico de procesos con tolerancias dimensionales certificadas bajo norma INEN. La innovación radica en la capacidad sistémica de producir con menor variabilidad y costo unitario verificable, no en el artefacto aislado."
    }
]

words = len(topics_test[0]["sample"].split())
print(f"Sample words: {words}")
assert words >= 80
print("OK!")
