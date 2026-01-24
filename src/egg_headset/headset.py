from . import EggHeadset

eeg = EggHeadset(port="COM4")  # Ustaw właściwy port

eeg.connect()
eeg.start()

run = True
while run:
    x = input("Wprowadź (exit aby zakończyć): ")
    if x == "exit":
        run = False
    else:
        eeg.annotate(x)

eeg.stop()
eeg.save("test.fif")
