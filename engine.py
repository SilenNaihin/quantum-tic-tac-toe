from qiskit import Aer
from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister
from qiskit import CompositeGate
from qiskit import execute
from composite_gates import cry,cnx,any_x,bus_or,x_bus
import numpy as np


class Move():
    def __init__(self,indices,player,q1=None,q2=None):
        """A data structure for game moves"""
        self.indices = indices
        self.player=player
        self.q1=q1
        self.q2=q2
    def __str__(self):
        return str([self.indices,self.player,self.q1,self.q2])

class Board():
    def __init__(self,x,y,print_info=False):
        #quantum register, classical register, quantum circuit.
        self.print_info=print_info
        self.q = QuantumRegister(1)
        self.c = ClassicalRegister(1)
        self.qc = QuantumCircuit(self.q, self.c)
        self.qc.cry = cry
        self.qc.x_bus = x_bus
        self.qc.cnx = cnx
        self.qc.any_x = any_x
        self.qc.bus_or = bus_or
        #the dimensions of the bord
        self.x=x
        self.y=y
        #To keep track of what is in each cell, no entanglement etc.
        #Provides a graphic of the game state.
        self.cells = np.empty((x,y),dtype=object)
        self.cells[:]='' #Initially game is empty.
        self.game_full = False
        self.moves = []

    def __str__(self):
        return str(self.cells)

    def add_move(self,indices,player):
        """Adds a move if it is non-clashing, otherwise passes it on"""
        for index in indices:
            if index[0] >= self.x:
                return 'Index out of range'
            if index[1] >= self.y:
                return 'Index out of range'
        status = self._add_move(indices,player)
        if status=='ok':
            if player==0:
                char = 'X'
            elif player==1:
                char = 'O'
            char+=str(len(self.moves))
            for index in indices:
                s = self.cells[index[0],index[1]]
                if s: #If the cell has some text
                    #Add char with a comma
                    self.cells[index[0],index[1]]+=' '+char
                else: #cell is empty so just add char
                    self.cells[index[0],index[1]]+=char
            print(self.cells)

        return status
    def _add_move(self,indices,player):
        """Actually adds the move if not clashing,
        otherwise passes it to _add_clashing_move"""
        if len(indices)==2:
            if indices[0]==indices[1]:
                indices = [indices[0]]
        num=len(indices)
        caught_clashes = False #turns true if all moves are safe clashes
        for existing_move in self.moves:
            for index in indices:
                if index in existing_move.indices:
                    if len(existing_move.indices)==1:
                        return 'overfull'
                        #This move will ALWAYS be there, if it can.
                        #hence, overfull.
                    else:
                        #captures any clash
                        caught_clashes = True
        if caught_clashes:
            return self._add_clashing_move(indices,player)
        else:
            #Reach this section if there are no clashes at all
            if num==1:
                self.moves.append(Move(indices,player)) #No control needed
                return 'ok'
            else:
                self.q.size+=2 #indicator qubit, and move qubit
                q1 = self.q[self.q.size-2] #To make this readable...
                q2 = self.q[self.q.size-1]
                self.qc.h(q1) #the last qubit in register.
                self.qc.x(q2)
                self.qc.cx(q1,q2)
                self.moves.append(Move(indices,player,q1,q2))
                return 'ok'

    def _add_clashing_move(self,indices,player):
        """Adds a clashing move"""
        if len(indices)==1: #100% of qubit is on one clashing spot.
            #This spot COULD be occupied.
            self.q.size+=1 #Only one bit needed, move happens or not.
            index = indices[0]
            bus = []
            for existing_move in self.moves:
                if index in existing_move.indices:
                    if index==existing_move.indices[0]:
                        bus.append(existing_move.q1)
                    elif index==existing_move.indices[1]:
                        bus.append(existing_move.q2)
            #Now if any entry on the bus is true, our qubit is false.
            self.qc.x(self.q[self.q.size-1]) # make it 1
            self.qc.any_x(self.qc,*bus,self.q[self.q.size-1])
            #negate is any dependents are true.
            #So the new move can happen if none of the others happen.
            self.moves.append(Move(indices,player,self.q[self.q.size-1]))
            return 'ok'
        elif len(indices)==2:
            #Check first spot is not occupied, then second spot if first
            #is not occupied.
            self.q.size+=2 #Two bits needed (maybe) for each index.
            #This can be optimized, in effect only one qubit is needed,
            #and its result indicates the selected qubit.
            #However, then some control qubit is needed too.
            #Since there are moves that could possibly be erased completely!
            bus0 = []
            bus1 = []
            for existing_move in self.moves:
                if indices[0] in existing_move.indices:
                    if indices[0]==existing_move.indices[0]:
                        bus0.append(existing_move.q1)
                    elif indices[0]==existing_move.indices[1]:
                        bus0.append(existing_move.q2)
                if indices[1] in existing_move.indices:
                    if indices[1]==existing_move.indices[0]:
                        bus1.append(existing_move.q1)
                    elif indices[1]==existing_move.indices[1]:
                        bus1.append(existing_move.q2)
            #Now if any entry on the bus is true, our first qubit is false.
            q1 = self.q[self.q.size-2] #a bit easier to look at (:
            q2 = self.q[self.q.size-1]
            if bus0:
                self.qc.x(q1)
                self.qc.cnx(self.qc,*bus0,q1)
            else: self.qc.h(q1)
            #And now the second qubit is 1 only if none of its competitors
            #are 1, and likewise if the previous qubit is zero.
            self.qc.x(q2)
            self.qc.bus_or(self.qc,q2,bus1,[q1])
            self.moves.append(Move(indices,player,q1,q2))
            return 'ok'

    def run(self):
        """Game loop"""
        self.running=True
        if self.print_info:
            print("  ")
            print("  ")
            print("            ============= Welcome to Quantum Tic Tac Toe! =============")
            print("  ")
            print("  ")
            print("  It's like regular tic tac toe but more confusing.")
            print("  The grid is still 3x3, and an empty cell looks like this: '' .")
            print("  You play two moves each turn, the number of the turn appearing beside your letter 'X1' .")
            print("  You move by typing in X and Y values from 0-2 to select boxes where your superimposed moves goes")
            print("  Neither of those moves are real, and act as a superposition of a real move.")
            print("  A superposition of real moves does not secure those spots, other players can attempy to occupy them too.")
            print("  If you move in is already occupied by another character, it will cause the two moves to be anti-correlated.")
            print("  This basically just means that the qubits are split up into parts of the full 100% of the spot.")
            print("  And so the game branches out into many possible simultaneous states.")
            print("  The outcome is then computed by simulation.")
            print("  Enter 'end' to end the game, and compute the winner(s).")
            print("                         ---------- Good luck! ----------")
            print("  ")
            print("  ")
            print("  ")
        while self.running:
            self.ask_player(0)
            self.ask_player(1)
        if self.game_full:
            self.compute_winner()

    def ask_player(self,player):
        key = "anything"
        """Ask a player for move details"""
        asking=False
        if self.running:
            asking = True
        while asking:
            if player==0:
                player_name = 'X'
            elif player==1:
                player_name = 'O'
            print("PLAYER "+player_name+"'s turn:")
            cells = self.question("Type '2' and press enter to continue:")
            if cells == '2':


                # while key != "":
                #     key = input('Hit Enter to continue')

                x1 = int(self.question('x1 position:'))
                y1 = int(self.question('y1 position:'))
                x2 = int(self.question('x2 position:'))
                y2 = int(self.question('y2 position:'))
                status = self.add_move([[y1,x1],[y2,x2]],player)
                if status == 'ok':
                    asking = False
                else: print(status)

            if not self.running:
                asking=False

    def question(self,text):
        """ask user a question"""
        if self.running:
            answer = input(text)
            if answer=='q':
                self.running=False
                return None
            elif answer=='end':
                self.game_full = True
                self.running = False
            else:
                return answer
        else: return None

    def compute_winner(self):
        """Find overall game winner, by finding winners of each outcome"""
        self.c.size = self.q.size #Make them the same
        self.qc.measure(self.q, self.c) #Measure
        backend = Aer.get_backend('qasm_simulator')
        job_sim = execute(self.qc, backend=backend, shots=100)
        sim_result = job_sim.result()
        print("simulation: ", sim_result)
        print(sim_result.get_counts(self.qc))
        self.counts = sim_result.get_counts(self.qc)
        for count in self.counts: #Takes key names
            c = list(count)[:-1] #splits key '1011' => ['1','0','1','1']
            c = c[::-1] #invert it so it goes 0 up...
            #Ignore the last bit since I dont know how to get rid of it
            #It is zero always.
            #The reason it is included is that I create a quantum register and
            #then start adding operations, quantum registers need at least one bit.
            counter = 0
            weight = self.counts[count]
            empty = np.zeros((self.x,self.y),dtype=str)
            for m in self.moves:
                if m.player == 0:
                    char = 'x'
                elif m.player==1:
                    char = 'o'
                result = []
                if m.q1:
                    result.append(c[counter])
                    counter+=1
                if m.q2:
                    result.append(c[counter])
                    counter+=1
                #print(result)
                if len(result) == len(m.indices):
                    #print(m)
                    if result[0]=='1':
                        empty[m.indices[0][0],m.indices[0][1]] = char
                    if len(result)>1:
                        if result[1]=='1':
                            if result[0]=='1':
                                print('problem! a move appeard in two places.')
                                print(m)
                            empty[m.indices[1][0],m.indices[1][1]] = char
                elif not result: #Then it was a classcal move
                    empty[m.indices[0][0],m.indices[0][1]] = char
            xscore,oscore=self.winners(empty)
            print('X Completed Rows: '+str(xscore))
            print('O Completed Rows: '+str(oscore))
            print('% Of This Outcome Happening:: '+str(weight))
            print(empty)

    def winners(self,empty):
        """Compute winners of a board"""
        oscore = 0
        xscore = 0
        for x in range(self.x):
            if empty[x,1]==empty[x,0] and empty[x,2]==empty[x,1]:
                if empty[x,0]=='o':
                    oscore+=1
                elif empty[x,0]=='x':
                    xscore +=1
        for y in range(self.y):
            if empty[1,y]==empty[0,y] and empty[2,y]==empty[0,y]:
                if empty[0,y]=='o':
                    oscore+=1
                elif empty[0,y]=='x':
                    xscore +=1
        if empty[0,0]==empty[1,1] and empty[1,1]==empty[2,2]:
            if empty[0,0]=='o':
                oscore+=1
            elif empty[0,0]=='x':
                xscore += 1
        if empty[2,0]==empty[1,1] and empty[1,1]==empty[0,2]:
            if empty[2,0]=='o':
                oscore+=1
            elif empty[2,0]=='x':
                xscore += 1
        return [xscore,oscore]

    def _populate_board(self):
        """Automatically populate as below, for testing purposes"""
        self.add_move([[2,2],[0,0]],1)
        self.add_move([[1,1],[1,2]],0)
        self.add_move([[1,2],[2,1]],1)
        self.add_move([[2,1]],0)
        self.add_move([[0,1]],1)
        self.add_move([[1,0]],0)
        self.add_move([[2,0]],1)
        self.add_move([[2,2]],0)
        self.add_move([[0,0]],1)
        self.add_move([[0,2]],0)
        self.add_move([[1,1]],1)
        self.add_move([[1,2]],0)
if __name__=="__main__":
    B= Board(3,3,True)
    B.run()
    #B._populate_board()
    #a = B.compute_winner()
