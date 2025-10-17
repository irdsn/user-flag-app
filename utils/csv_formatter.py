##################################################################################################
#                                            OVERVIEW                                            #
#                                                                                                #
# Fixes CSV files exported from Excel/Numbers by converting encoding to UTF-8 and normalizing LF.#
##################################################################################################

##################################################################################################
#                                            IMPORTS                                             #
##################################################################################################

import io
import os

##################################################################################################
#                                        CONFIGURATION                                           #
##################################################################################################

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(base_dir, "inputs", "input_S.csv")
tmp = os.path.join(base_dir, "inputs", "input_fixed.csv")

##################################################################################################
#                                        IMPLEMENTATION                                          #
##################################################################################################

with io.open(src, "r", encoding="utf-8", errors="ignore") as fin, io.open(tmp, "w", encoding="utf-8", newline="\n") as fout:
    for line in fin:
        # Replace carriage returns and stray characters
        clean = line.replace("\r", "\n").replace("%", "").strip()
        if clean:
            fout.write(clean + "\n")

os.replace(tmp, src)
print("✅ CSV normalized successfully:", src)
