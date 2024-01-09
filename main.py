from machine import Pin
from picozero import Speaker


MIN_FREQ = 130.81
TOTAL_NOTES = 65
SCALE_LENGTH = 16
FREQS = [round(MIN_FREQ * 2**(x/12)) for x in range(TOTAL_NOTES)]


# Assign pins to keys available on the keypads
NOTEPAD = [['16', '15', '14', '13'],
          ['12', '11', '10', '9'],
          ['8', '7', '6', '5'],
          ['4', '3', '2', '1']]

FUNCPAD = [['-', '9', '8', '7'],
           ['+', '6', '5', '4'],
           ['O', '3', '2', '1'],
           ['X', 'T', '#', 'A']]


# Class to store and update musical information and perform notes
class Controller():
    
    # Initialize controller with default scale, define dedicated speaker and keypad pins
    def __init__(self, default_freq, speaker_pin, note_row_pins, note_col_pins, func_row_pins, func_col_pins):
        self.prev_note = None
        self.prev_func = None
        self.arp_mode = False
        self.arp_backwards = False
        
        self.arp_length = 4
        self.tempo = 120
        self.quit_counter = 0
        self.reset_counter = 0
        self.default_freq = default_freq
        
        self.scale = []
        self.make_scale(default_freq, 1)
        
        self.speaker = Speaker(speaker_pin)
        self.note_row_pins = []
        self.note_col_pins = []
        self.func_row_pins = []
        self.func_col_pins = []
        
        for x in range(4):
            self.note_row_pins.append(Pin(note_row_pins[x], Pin.OUT))
            self.note_row_pins[x].value(1)
            self.note_col_pins.append(Pin(note_col_pins[x], Pin.IN, Pin.PULL_DOWN))
            self.note_col_pins[x].value(0)
            
            self.func_row_pins.append(Pin(func_row_pins[x], Pin.OUT))
            self.func_row_pins[x].value(1)
            self.func_col_pins.append(Pin(func_col_pins[x], Pin.IN, Pin.PULL_DOWN))
            self.func_col_pins[x].value(0)
            
    
    # Reset controller to default parameters
    def reset(self):
        self.arp_mode = False
        self.arp_backwards = False
        self.arp_length = 4
        self.tempo = 120
        self.quit_counter = 0
        self.reset_counter = 0
        self.make_scale(self.default_freq, 1)
            
    
    # Get pressed keys and react accordingly
    def operate(self):
        while True:
            note_key = self.get_note_pressed()
            func_key = self.get_func_pressed()
            
            if note_key is None:
                self.prev_note = None
                self.speaker.off()
            else:
                if self.arp_mode == True:
                    self.arpeggiate(note_key)
                    self.arp_mode = False
                elif note_key != self.prev_note:
                    print(f"Playing Degree {note_key}")
                    self.speaker.off()
                    self.speaker.play(self.scale[int(note_key) - 1], 10, wait=False)
                    self.prev_note = note_key
            
            if func_key is not None:
                if func_key != 'X':
                    self.quit_counter = 0
                if func_key != 'O':
                    self.reset_counter = 0
                    
                if func_key == 'A' and self.prev_func != 'A':
                    self.set_arpeggiation()
                elif func_key == '#' and self.prev_func != '#':
                    self.transpose()
                elif func_key == 'T' and self.prev_func != 'T':
                    self.set_tempo()
                elif func_key == '+' and self.prev_func != '+':
                    self.change_octave(1)
                elif func_key == '-' and self.prev_func != '-':
                    self.change_octave(-1)
                elif func_key == 'X' and self.prev_func != 'X':
                    self.quit_counter += 1
                    if self.quit_counter >= 3:
                        print("Quitting...")
                        return
                    print(f"Quit Counter: {self.quit_counter}")
                elif func_key == 'O' and self.prev_func != 'O':
                    self.reset_counter += 1
                    if self.reset_counter >= 3:
                        print("Resetting...")
                        self.reset()
                    else:
                        print(f"Reset Counter: {self.reset_counter}")

            self.prev_func = self.get_func_pressed()
  

    # Get the current key on the notepad pressed by the user
    def get_note_pressed(self):
        for row in range(4):
            for col in range(4):
                self.note_row_pins[row].high()
                if self.note_col_pins[col].value() == 1:
                    self.note_row_pins[row].low()
                    return NOTEPAD[row][col]
                          
            self.note_row_pins[row].low()
        return None
    
    
    # Get the current key on the funcpad pressed by the user
    def get_func_pressed(self):
        for row in range(4):
            for col in range(4):
                self.func_row_pins[row].high()
                if self.func_col_pins[col].value() == 1:
                    self.func_row_pins[row].low()
                    return FUNCPAD[row][col]
                          
            self.func_row_pins[row].low()
        return None
    
    
    # Wait for a specific func key to be pressed by the user
    def wait_for(self, keys = None, none=False, digit=False):
        while True:
            key = self.get_func_pressed()
            if key is None:
                if none:
                    return None
            elif (keys != None and key in keys) or (digit and key.isdigit()):
                return key
        
        
    # Make a major or minor scale for a given base frequency
    def make_scale(self, base_freq, quality):
        # scale_rules[0][x] = minor, scale_rules[1][x] = major
        # The notepad plays 16 scale degrees so we have 15 steps to account for
        scale_rules = [[2, 1, 2, 2, 1, 2, 2, 2, 1, 2, 2, 1, 2, 2, 2],
                       [2, 2, 1, 2, 2, 2, 1, 2, 2, 1, 2, 2, 2, 1, 2]]
        
        self.scale = [base_freq]
        index = FREQS.index(base_freq)
        for step in scale_rules[quality]:
            index += step
            self.scale.append(FREQS[index])
        
    
    # Play the arpeggio of a given scale degree
    # Arpeggiation occurs at the 16th note duration in the selected tempo
    def arpeggiate(self, degree):
        duration = 60 / self.tempo / 4
        
        while True:
            arpeggio = self.make_arpeggio(self.scale[int(degree) - 1])
            print(f"Arpeggiating on degree {degree} with a length of {self.arp_length}")
            no_change = True
            
            while no_change:
                for freq in arpeggio:
                    self.speaker.play(freq, duration)
                    if self.get_func_pressed() == 'X':
                        print("Arp interrupted")
                        return
                    
                note_key = self.get_note_pressed()
                func_key = self.get_func_pressed()
                
                if func_key == 'A':
                    self.arp_mode = False
                    print("End of arp. Arp mode = False")
                    return
                if func_key == 'O':
                    print("End of arp.")
                    return
                elif func_key == '+':
                    self.change_octave(1)
                    no_change = False
                elif func_key == '-':
                    self.change_octave(-1)
                    no_change = False
                
                if note_key is not None and note_key != degree:
                    degree = note_key
                    no_change = False
                
    
    # Make an arpeggio based on a given frequency
    # Default arpeggios only include the 1st, 3rd, and 5th scale degrees 
    def make_arpeggio(self, freq):
        arpeggio = [freq]
        overflow_index = 0
        
        while len(arpeggio) < self.arp_length:
            # If the arpeggio is length 3 or more, we have already determined the 1st, 3rd, and 5th scale degrees
            # Therefore, we can just octave everything up to get the next note
            if len(arpeggio) >= 3:
                next_note = FREQS.index(arpeggio[-3]) + 12
                # If the next note is out of range, repeat the arpeggio from the start
                if next_note >= TOTAL_NOTES:
                    arpeggio.append(arpeggio[overflow_index])
                    overflow_index += 1
                else:
                    arpeggio.append(FREQS[next_note])
                    
            # If arpeggio length is less than 3, we need to determine the next notes based on the objects scale
            # 3rd scale degree is 2 away from 1st, and 5th scale degree is 2 away from 3rd
            else:
                prev_freq = arpeggio[-1]
                if prev_freq in self.scale and self.scale.index(prev_freq) + 2 < SCALE_LENGTH:
                    arpeggio.append(self.degrees_from(prev_freq, 2))
                # If next degree is not in scale, find next degree an octave lower, and octave up
                else:
                    arpeggio.append(self.freqs_from(self.degrees_from(self.freqs_from(prev_freq, -12), 2), 12))
                    
        if self.arp_backwards:
            arpeggio.extend(arpeggio[::-1][1 : self.arp_length - 1])
        return arpeggio
                                    
    
    # Find the frequency a certain amount of steps away from freq in self.scale
    def degrees_from(self, freq, steps):
        return self.scale[self.scale.index(freq) + steps]
    
    
    # Find the frequency a certain amount of steps away from the freq in FREQS
    def freqs_from(self, freq, steps):
        return FREQS[FREQS.index(freq) + steps]

    
    # Prompt the user for arpeggio settings
    def set_arpeggiation(self):
        print("Arpeggio Mode")
        arp_mode = self.arp_mode
        arp_backwards = self.arp_backwards
        arp_length = self.arp_length
        print(f"A. Toggle arp mode (currently {arp_mode})\n+. Toggle backwards arp (currently {arp_backwards})\n",
              f"Digit. Set arp length (currently {arp_length})\n#. Define custom sequence\nX. Exit and cancel\nO. Exit and save")
        
        while True:
            self.wait_for(none=True)
            key = self.wait_for(['A', '+', '#', 'X', 'O'], digit=True)
            
            if key == 'X':
                print("Cancelled settings")
                break
            elif key == 'O':
                print("Saved settings")
                self.arp_mode = arp_mode
                self.arp_backwards = arp_backwards
                self.arp_length = arp_length
                break
            elif key == 'A':
                arp_mode = not arp_mode
                print(f"Arp mode = {arp_mode}")
            elif key == '+':
                arp_backwards = not arp_backwards
                print(f"Arp backwards = {arp_backwards}")
            elif key.isdigit():
                print("Expand new arp length. '#' is zero. Press 'O' once finished, or 'X' to quit:")
                new_length = key
                print(f"> {new_length} notes")
                
                while True:
                    self.wait_for(none=True)
                    key = self.wait_for(['#', 'O', 'X'], digit=True)
                    
                    if key.isdigit():
                        new_length += key
                        print(f"> {new_length} notes")
                    elif key == '#':
                        new_length += '0'
                        print(f"> {new_length} notes")
                    elif key == 'O':
                        print("Arp length confirmed")
                        arp_length = int(new_length)
                        break
                    else:
                        print("Arp length canceled")
                        break
        
    
    # Prompt the user and set the tempo
    def set_tempo(self):
        print(f"Enter new tempo (currently {self.tempo})\n('#' is zero, 'O' to confirm, 'X' to quit):")
        new_tempo = ""
        
        while True:
            self.wait_for(none=True)
            key = self.wait_for(['#', 'O', 'X'], digit=True)
            
            if key.isdigit():
                new_tempo += key
                print(f"> {new_tempo} bpm")
            elif key == '#':
                new_tempo += '0'
                print(f"> {new_tempo} bpm")
            elif key == 'O':
                print(f"New tempo confirmed: {new_tempo} bpm")
                self.tempo = int(new_tempo)
                break
            else:
                print("Tempo change canceled")
                break


    # Remove frequencies before new_base, and extend the scale to SCALE_LENGTH
    # Allows the mode of the scale to change
    def extend_scale(self, new_base):
        for _ in range(new_base):
            extend_steps = FREQS.index(self.scale[-7]) - FREQS.index(self.scale[-8])
            self.scale.append(self.freqs_from(self.scale[-1], extend_steps))
            del(self.scale[0])

    
    # Octave the entire scale up or down
    def change_octave(self, direction):
        octave = 12 * direction
        if FREQS.index(self.scale[-1]) + octave >= TOTAL_NOTES or FREQS.index(self.scale[0]) + octave < 0:
            print("Error: octave out of range")
        else:
            if direction == 1:
                print("Octave +")
            else:
                print("Octave -")
            self.scale = [self.freqs_from(freq, octave) for freq in self.scale]


    # Prompt the user and transpose scale to different keys or modes
    def transpose(self):
        print("Transpose Mode\nPress a degree to transpose to, or 'X' to quit:")
        key = self.wait_for(['X'], digit=True)
        
        if key == 'X':
            print("Exit Transpose Mode")
        else:
            new_base = int(key)
            print(f"Transposing to {new_base}. Enter quality:\n('+' = major, '-' = minor, 'O' = in current key, 'X' = quit)")
            new_base_freq = self.scale[new_base - 1]
            key = self.wait_for(['+', '-', 'O', 'X'])
            
            if key == '+':
                self.make_scale(new_base_freq, 1)
                print(f"Transposed to major {new_base}")
            elif key == '-':
                self.make_scale(new_base_freq, 0)
                print(f"Transposed to minor {new_base}")
            elif key == 'O':
                self.extend_scale(new_base - 1)
                print(f"Transposed to {new_base} in current key")
        

if __name__ == "__main__":

        default_freq = 262
        speaker = 16
        
        note_rows = [15, 14, 13, 12]
        note_cols = [11, 10, 9, 8]
        func_rows = [7, 6, 5, 4]
        func_cols = [3, 2, 1, 0]
        
        print("Initializing Controller...")
        controller = Controller(default_freq, speaker, note_rows, note_cols, func_rows, func_cols)
        
        print("Play some tunes!")
        controller.operate()
        
        print("Quit controller. Goodbye :)")
