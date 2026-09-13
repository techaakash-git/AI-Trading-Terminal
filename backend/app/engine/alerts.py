class CrossingStateMachine:
    def __init__(self): self._state={}
    def evaluate(self,key,value,threshold,direction):
        prev=self._state.get(key); self._state[key]=value
        if prev is None:return False
        return (prev<threshold<=value) if direction=='up' else (prev>threshold>=value)
