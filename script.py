#! /usr/bin/env python3

import sys, os

# benchmarks amb els que farem les proves
benchmark = ["ammp", "applu", "eon", "equake", "vpr"]


# configuració de la memòria principal
ram = {
    "lat1": "300",
    "lat2": "2",
    "width": "32"
}
ram_se = "-mem:lat " + ram["lat1"] + " " + ram["lat2"] + " -mem:width " + ram["width"];

# configuració predictors
predictor = {
    "pred": "2lev",			#Cambiar entre nottaken,taken,perfect,bimodal i 2levl
    "l2size": "1024",			#Per a predictors bimodals i 2lev
    "l1size": "64",
    "logl2": "10",			#3 (8), 5 (32), 7 (128), 9 (512), 11 (2048)	(l2size = PHT)

}
#pred_se = "-bpred " + predictor["pred"];	#Estatics

#pred_se = "-bpred " + predictor["pred"] + " -bpred:bimod " + predictor["l2size"];	#Bimodal

#2lev Gshare
#pred_se = "-bpred " + predictor["pred"] + " -bpred:2lev " + predictor["l1size"] + " " + predictor["l2size"] + " " + predictor["logl2"] + " 1";	

#2lev GAG
#pred_se = "-bpred " + predictor["pred"] + " -bpred:2lev " + predictor["l1size"] + " " + predictor["l2size"] + " " + predictor["logl2"] + " 0";

#2lev PAG
pred_se = "-bpred " + predictor["pred"] + " -bpred:2lev " + predictor["l1size"] + " " + predictor["l2size"] + " " + predictor["logl2"] + " 0";		



config = ["", "", ""]
j = 0

# Comprovo paràmetres d'entrada
if (len(sys.argv) >= 3):
    results_path = os.path.abspath(sys.argv[1]) + "/"
    specs_path = os.path.abspath(sys.argv[2]) + "/"
elif (len(sys.argv) == 2):
    results_path = os.path.abspath(sys.argv[1]) + "/"
    specs_path = "/home/milax/Escriptori/P1AC/Specs2000/"
else:
    results_path = os.getcwd() + "/resultats/"
    specs_path = "/home/milax/Escriptori/P1AC/Specs2000/"

for i in benchmark:
    os.chdir(specs_path + i + "/data/ref")

    inst = f"sim-outorder -fastfwd 100000000 -max:inst 100000000 {ram_se} {pred_se} -redir:sim {results_path}{i}.txt ../../exe/{i}.exe "
    #inst = f"sim-bpred -fastfwd 100000000 -max:inst 100000000 {pred_se} -redir:sim {results_path}{i}.txt ../../exe/{i}.exe "
   
    
    if i == "eon":
        inst += f"chair.control.cook chair.camera chair.surfaces chair.cook.ppm ppm pixels_out.cook > {results_path}{i}.out 2> {results_path}{i}.err"
    elif i == "equake":
        inst += f"< inp.in > {results_path}{i}.out 2> {results_path}{i}.err"
    elif i == "vpr":
        inst += f"net.in arch.in place.out dum.out -nodisp -place_only -init_t 5 -exit_t 0.005 -alpha_t 0.9412 -inner_num 2 > place_log.out 2> place.log.err"
    elif i == "ammp":
        inst += f"< ammp.in > {results_path}{i}.out 2> {results_path}{i}.err"
    elif i == "applu":
        inst += f"< applu.in > {results_path}{i}.out 2> {results_path}{i}.err"
    
    print(inst);
    
    os.system(inst)

