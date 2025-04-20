def decide_winner(solutions):
    """
    solutions: dict donde clave=usuario, valor=código entregado
    Devuelve una tupla (ganador, justificación).
    """
    # Stub hardcodeado para pruebas
    jugadores = list(solutions.keys())
    winner = jugadores[0]  # o cualquier lógica de prueba
    justification = f"Por ahora {winner} gana porque es el primero en la lista."
    return winner, justification