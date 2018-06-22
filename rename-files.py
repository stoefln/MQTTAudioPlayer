import glob, os, sys

def rename(dir, pattern):
    print("Renaming files: ")
    names = ["A1","A2","A3","A4","A5", 
             "B1","B2","B3","B4","B5", 
             "C1","C2","C3","C4","C5", 
             "D1","D2","D3","D4","D5", 
             "E1","E2","E3","E4","E5",
    ]
    i = 0
    for pathAndFilename in glob.iglob(os.path.join(dir, pattern)):
        title, ext = os.path.splitext(os.path.basename(pathAndFilename))
        
        if(i<25):
            
            name = names[i]
            print("renaming: "+ title+ext + " to "+name + ext)
            os.rename(pathAndFilename, 
                os.path.join(dir, name + ext))
        i = i+1

raw_input("Attention: You need to run this script in the directory you want to rename files! Take care!")
rename( r'.', r'*.wav')
raw_input("Press Enter to continue...")