import re

class State:
    NO_STATE = 0
    START = 1
    END = 2


PATTERN = re.compile(r'(#|(\/\/))\s(Start|End)\s(Example)\s\d+', re.I)

def main():
  ## Set state to initial
  state = State.NO_STATE
  line_number
  
  f = open('test_examples.py', 'r')
  for line in f:
      if re.search(PATTERN, line):
          if line.lower().find('start') > -1:
              if state == State.START:
                  raise Exception('Detected START EXAMPLE. Expected END EXAMPLE')
              state = State.START
          elif line.lower().find('end') > -1:
              if state == (State.NO_STATE or State.END):
                  raise Exception('Detected END EXAMPLE. Expected START EXAMPLE')
              state = State.END
              
          print line

main()