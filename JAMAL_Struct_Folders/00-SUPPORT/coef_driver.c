/************************************************************************************************
 * **********************************************************************************************
 * * Program name      : COEF DRIVER
 * *
 * * Author            : Maximiliano A. F. Souza
 * *
 * * Date created      : 20231201
 * *
 * * Purpose           : CL-Drive initiates an alpha sweep to analyze Drag-Rise, targeting a 
 * *                     specific coefficient of lift (CL). Similarly, CY-Driver can be done
 * *                     through a beta sweep.
 * *
 * * Revision History  :
 * *
 * * Date        Author                      Rev.   Changes made
 * * 20231201    Maximiliano A. F. Souza     1      Released version 1
 * *
 *  *********************************************************************************************
 *  ====================================== DESCRIPTION ==========================================
 * * This function actively modifies the velocity components during iterative 
 * * simulations to attain predefined target coefficient values. Here's how it operates:
 * * 
 * * Function Workflow:
 * * 
 * * Slope Curve Estimation: The function initiates by estimating the slope curve 
 * * of the desired coefficient (CLS for Alpha sweep drive or CYS for Beta sweep drive) 
 * * concerning changes in the angle of attack (Alpha) or sideslip (Beta), respectively. 
 * * This estimation involves making slight adjustments to the angle of attack or sideslip.
 * * 
 * * Angle of Attack or Sideslip Update: Subsequently, the function iteratively updates 
 * * either the Alpha or Beta angle. It continues to adjust this angle until the difference 
 * * between the calculated coefficient and the desired target coefficient value 
 * * falls below a predefined residue threshold.
 * * 
 * * Note: To ensure the success of this process, it is crucial that the coefficients 
 * * curve slope remains relatively constant throughout the variation in angles.
*************************************************************************************************/
#include "udf.h"
#include <stdio.h>
int iter_update, iter_slope, last_iter;
int delta_iter_update           = %delta_iter_update%;     /* Maximum allowable iterations before updating the Angle of Attack (Alpha) or Sideslip angle (Beta). */
int delta_iter_slope            = %delta_iter_slope%;     /* Number of iterations for assessing the slope curve of dCL_dAlpha or dCY_dBeta. */
int iter_start_process          = %iter_start_process%;    /* Starting iteration for the Coef Driver function. */
int next_case_iter              = %next_case_iter%;    /* Total number of iterations of the next case.*/
int i = 0;
real Coef_target_vec[%size%]    = {%Coef_target%};    /* Vector of target coefficients. */
real Delta_CL_tol               = %Delta_CL_tol%;   /* Residual tolerance for the Delta CL. */
real Delta_CY_tol               = %Delta_CY_tol%;  /* Residual tolerance for the Delta CY. */
real Delta_Alpha_deg_slope      = %Delta_Alpha_deg_slope%;     /* Delta Alpha for evaluating the slope curve dCL_dAlpha. */
real Delta_Beta_deg_slope       = %Delta_Beta_deg_slope%;     /* Beta threshold for evaluating the slope curve dCY_dBeta. */ 
real Delta_angle_deg_max        = %Delta_angle_deg_max%;    /* Maximum allowed alpha update. */
real Alpha_deg                  = %Alpha_deg%;     /* The starting Alpha value for the process is 0 only if this is a Alpha sweep driver. */
real Beta_deg                   = %Beta_deg%;     /* The starting Beta value for the process is 0 only if this is a Beta sweep driver. */
real Mach_vec[%size_mach%]      = {%Mach%};     /* Vector of Mach numbers.*/
real Mach, Coef_target;
real CDS, CYS, CLS, CRS_, CMS, CNS, CXB, CYB, CZB, CRB, CMB, CNB, CLB, CDB, Coef1, Coef2, Delta_Coef, Delta_Coef_target, slope, Delta_Coef_tol;
real angle_rad, Delta_angle_rad, Delta_angle_deg, Delta_angle_rad_max, Delta_angle_rad_slope;
real Alpha_rad, Delta_Alpha_deg, Delta_Alpha_rad, Delta_Alpha_rad_slope;
real Beta_rad, Delta_Beta_deg, Delta_Beta_rad, Delta_Beta_rad_slope;
double x_flow_direction  = %x_flow_direction%; 
double y_flow_direction  = %y_flow_direction%;
double z_flow_direction  = %z_flow_direction%;
char driver_coef[] = "%coef_driver_mode%";
char mach_sweep[] = "%mach_sweep%";
/* The coef_driver_function serves as the core of the code, situated within the DEFINE_EXECUTE_AT_END macro, 
 * which executes at the end of each iteration. This function is responsible for acquiring the coefficient 
 * report values and conducting all necessary calculations. 
 * Below, within the DEFINE_PROFILE macros, you will find the x_component_flow_direction, y_component_flow_direction, and z_component_flow_direction 
 * functions, which update the boundary condition definitions for the velocity components. */
DEFINE_EXECUTE_AT_END(coef_driver_function){
    int nrOfvalues_cl=0;
    int nrOfvalues_cd=0;
    int nrOfvalues_cy=0;
    int nrOfvalues_cr=0;
    int nrOfvalues_cm=0;
    int nrOfvalues_cn=0;
    real *cl_z_axis_cfd_model_body, *cd_x_axis_cfd_model_body, *cy_y_axis_cfd_model_body, *cr_x_axis_cfd_model_body, *cm_y_axis_cfd_model_body, *cn_z_axis_cfd_model_body;
    int *ids_cl, *ids_cd, *ids_cy, *ids_cr, *ids_cm, *ids_cn;
    int index_cl, index_cd, index_cy, index_cr, index_cm, index_cn;
    int rv_cl, rv_cd, rv_cy, rv_cr, rv_cm, rv_cn;

    FILE *fileout;

    if (N_ITER == 1){
        fileout = fopen ("albe.out","w");
        if (strcmp(driver_coef, "CLS") == 0){
            fprintf (fileout,"%9s %9s %9s %9s %9s %9s %9s\n", "CLTARGET", "CLCURR", "MACH", "ALPHA", "BETA", "CLa", "CLB");    
        }
        else{
            fprintf (fileout,"%9s %9s %9s %9s %9s %9s %9s\n", "CYTARGET", "CYCURR", "MACH", "ALPHA", "BETA", "CYb", "CYB");
        }
        fclose (fileout);
        Mach = Mach_vec[0];
        Coef_target = Coef_target_vec[0];
        iter_update = 0;
        iter_slope = 0;
    }

    /* Get force and moment coefficients from report definitions in the CFD model body axis system, 
     * where the X-axis is oriented rearward, and the Z-axis points upward. */
    rv_cl = Get_Report_Definition_Values("clzb", 0, &nrOfvalues_cl, NULL, NULL,NULL);
    cl_z_axis_cfd_model_body = (real*) malloc(sizeof(real)* nrOfvalues_cl);
    ids_cl = (int*) malloc(sizeof(int)* nrOfvalues_cl);
    rv_cl = Get_Report_Definition_Values("clzb", 0, NULL, cl_z_axis_cfd_model_body, ids_cl, &index_cl);

    rv_cd = Get_Report_Definition_Values("cdxb", 0, &nrOfvalues_cd, NULL, NULL,NULL);
    cd_x_axis_cfd_model_body = (real*) malloc(sizeof(real)* nrOfvalues_cd);
    ids_cd = (int*) malloc(sizeof(int)* nrOfvalues_cd);
    rv_cd = Get_Report_Definition_Values("cdxb", 0, NULL, cd_x_axis_cfd_model_body, ids_cd, &index_cd);

    rv_cy = Get_Report_Definition_Values("cyyb", 0, &nrOfvalues_cy, NULL, NULL,NULL);
    cy_y_axis_cfd_model_body = (real*) malloc(sizeof(real)* nrOfvalues_cy);
    ids_cy = (int*) malloc(sizeof(int)* nrOfvalues_cy);
    rv_cy = Get_Report_Definition_Values("cyyb", 0, NULL, cy_y_axis_cfd_model_body, ids_cy, &index_cy);

    rv_cr = Get_Report_Definition_Values("crxb", 0, &nrOfvalues_cr, NULL, NULL,NULL);
    cr_x_axis_cfd_model_body = (real*) malloc(sizeof(real)* nrOfvalues_cr);
    ids_cr = (int*) malloc(sizeof(int)* nrOfvalues_cr);
    rv_cr = Get_Report_Definition_Values("crxb", 0, NULL, cr_x_axis_cfd_model_body, ids_cr, &index_cr);

    rv_cm = Get_Report_Definition_Values("cmyb", 0, &nrOfvalues_cm, NULL, NULL,NULL);
    cm_y_axis_cfd_model_body = (real*) malloc(sizeof(real)* nrOfvalues_cm);
    ids_cm = (int*) malloc(sizeof(int)* nrOfvalues_cm);
    rv_cm = Get_Report_Definition_Values("cmyb", 0, NULL, cm_y_axis_cfd_model_body, ids_cm, &index_cm);

    rv_cn = Get_Report_Definition_Values("cnzb", 0, &nrOfvalues_cn, NULL, NULL,NULL);
    cn_z_axis_cfd_model_body = (real*) malloc(sizeof(real)* nrOfvalues_cn);
    ids_cn = (int*) malloc(sizeof(int)* nrOfvalues_cn);
    rv_cn = Get_Report_Definition_Values("cnzb", 0, NULL, cn_z_axis_cfd_model_body, ids_cn, &index_cn);

    /* Converting the force and Moment coefficients to the aircraft body axis system 
     * (X pointing forward and Z downwards). */
    CXB = cd_x_axis_cfd_model_body[0]*(-1.0);
    CYB = cy_y_axis_cfd_model_body[0];
    CZB = cl_z_axis_cfd_model_body[0]*(-1.0);
    CRB = cr_x_axis_cfd_model_body[0]*(-1.0);
    CMB = cm_y_axis_cfd_model_body[0];
    CNB = cn_z_axis_cfd_model_body[0]*(-1.0);

    /* CDB and CLB inverted (-1 multiplied) to conform to conventional expectations.*/
    CLB = CZB*(-1.0);
    CDB = CXB*(-1.0);

    Alpha_rad = Alpha_deg * M_PI / 180.0;
    Beta_rad = Beta_deg * M_PI / 180.0;
    
    /* The following coefficients are transformed from body axis to Stability axis,
     * with CDS and CLS inverted (-1 multiplied) to conform to conventional expectations. */
    CDS =  (CXB*cos(Alpha_rad) + CZB*sin(Alpha_rad))*(-1.0);
    CYS =   CYB;
    CLS =  (CZB*cos(Alpha_rad) - CXB*sin(Alpha_rad))*(-1.0);
    CRS_=   CRB*cos(Alpha_rad) + CNB*sin(Alpha_rad);
    CMS =   CMB;
    CNS =   CNB*cos(Alpha_rad) - CRB*sin(Alpha_rad);

    if (N_ITER > 1){
        if (N_ITER == iter_update + 1 || N_ITER == iter_slope + 1){
            if (fabs(Delta_Coef_target) > Delta_Coef_tol){
                if (strcmp(driver_coef, "CLS") == 0){
                    Message0("\n  ########################## CL-DRIVER UPDATE ##########################\n\n");
                    Message0("  %9s %9s %9s %9s %9s %9s %9s\n", "CLTARGET", "CLCURR", "MACH", "ALPHA", "BETA", "CLa", "CLB");
                    Message0("  %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f\n\n", Coef_target, CLS, Mach, Alpha_deg, Beta_deg, slope, CLB);
                    Message0("  ######################################################################\n\n");
                }
                else{
                    Message0("\n  ########################## CY-DRIVER UPDATE ##########################\n\n");
                    Message0("  %9s %9s %9s %9s %9s %9s %9s\n", "CYTARGET", "CYCURR", "MACH", "ALPHA", "BETA", "CYb", "CYB");
                    Message0("  %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f\n\n", Coef_target, CYS, Mach, Alpha_deg, Beta_deg, slope, CYB);
                    Message0("  ######################################################################\n\n");
                }
            }
            else if (N_ITER != iter_slope){
                if (strcmp(driver_coef, "CLS") == 0){
                    Message0("\n  ######## CL-DRIVER UPDATE INTERRUPTED AT TOLERANCE %9.6f #########\n\n", Delta_Coef_target);
                    Message0("  %9s %9s %9s %9s %9s %9s %9s\n", "CLTARGET", "CLCURR", "MACH", "ALPHA", "BETA", "CLa", "CLB");
                    Message0("  %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f\n\n", Coef_target, CLS, Mach, Alpha_deg, Beta_deg, slope, CLB);
                    Message0("  ######################################################################\n\n");
                }
                else{
                    Message0("\n  ######## CY-DRIVER UPDATE INTERRUPTED AT TOLERANCE %9.6f #########\n\n", Delta_Coef_target);
                    Message0("  %9s %9s %9s %9s %9s %9s %9s\n", "CYTARGET", "CYCURR", "MACH", "ALPHA", "BETA", "CYb", "CYB");
                    Message0("  %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f\n\n", Coef_target, CYS, Mach, Alpha_deg, Beta_deg, slope, CYB);
                    Message0("  ######################################################################\n\n");
                }
            }
        }
    }

    if (N_ITER == next_case_iter){

        if (strcmp(driver_coef, "CLS") == 0){
            Message0("\n  ######################### CL-DRIVER CONCLUDED ########################\n\n");
            Message0("  %9s %9s %9s %9s %9s %9s %9s\n", "CLTARGET", "CLCURR", "MACH", "ALPHA", "BETA", "CLa", "CLB");
            Message0("  %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f\n\n", Coef_target, CLS, Mach, Alpha_deg, Beta_deg, slope, CLB);
            Message0("  ######################################################################\n\n");
        }
        else{
            Message0("\n  ######################### CY-DRIVER CONCLUDED ########################\n\n");
            Message0("  %9s %9s %9s %9s %9s %9s %9s\n", "CYTARGET", "CYCURR", "MACH", "ALPHA", "BETA", "CYb", "CYB");
            Message0("  %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f\n\n", Coef_target, CYS, Mach, Alpha_deg, Beta_deg, slope, CYB);
            Message0("  ######################################################################\n\n");
        }

        #if RP_HOST
        fileout = fopen ("albe.out","a");
        if (strcmp(driver_coef, "CLS") == 0){
            fprintf (fileout,"%9.6f %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f\n", Coef_target, CLS, Mach, Alpha_deg, Beta_deg, slope, CLB);
        }
        else{
            fprintf (fileout,"%9.6f %9.6f %9.6f %9.6f %9.6f %9.6f %9.6f\n", Coef_target, CYS, Mach, Alpha_deg, Beta_deg, slope, CYB);
        }
        fclose (fileout);
        #endif

        if (strcmp(mach_sweep, "TRUE") == 0){
            iter_start_process = N_ITER + %delta_iter%*0.4;
            delta_iter_slope = %delta_iter%*0.2;
            delta_iter_update = %delta_iter%*0.1;
            next_case_iter = N_ITER + %delta_iter%;
            last_iter = %next_case_iter% + (%size_mach% - 1)*%delta_iter%;
            if (N_ITER < last_iter){
              i = i + 1;
              Mach = Mach_vec[i];
            }
        }
        else{
            next_case_iter = N_ITER + %delta_iter%;
            last_iter = %next_case_iter% + (%size% - 1)*%delta_iter%;
            if (N_ITER < last_iter){
              i = i + 1;
              Coef_target = Coef_target_vec[i];
            }
        }
    }


    if (N_ITER == iter_start_process){
        /* Alpha Sweep Driver. */
        if (strcmp(driver_coef, "CLS") == 0){
            Coef1 = CLS;
            Delta_Alpha_rad_slope = Delta_Alpha_deg_slope * M_PI / 180.0;
            Alpha_rad = Alpha_rad + Delta_Alpha_rad_slope;
            Alpha_deg = Alpha_rad/M_PI * 180.0;
            Delta_Alpha_rad = Alpha_rad;
            Delta_Alpha_deg = Alpha_deg;
        } 
        /* Beta Sweep Driver. */
        if (strcmp(driver_coef, "CYS") == 0){
            Coef1 = CYS;
            Delta_Beta_rad_slope = Delta_Beta_deg_slope * M_PI / 180.0;
            Beta_rad = Beta_rad + Delta_Beta_rad_slope;
            Beta_deg = Beta_rad/M_PI * 180.0;
            Delta_Beta_rad = Beta_rad;
            Delta_Beta_deg = Beta_deg;
        }

        x_flow_direction =  cos(Alpha_rad)*cos(Beta_rad);
        y_flow_direction = -cos(Alpha_rad)*sin(Beta_rad);
        z_flow_direction =  sin(Alpha_rad);

        iter_slope = iter_start_process + delta_iter_slope;
        iter_update = iter_slope;
        if (strcmp(driver_coef, "CLS") == 0){
            Message0("\n  START EVALUATION OF CLa\n\n");
        }
        else{
            Message0("\n  START EVALUATION OF CYb\n\n");    
        }
           
    }

    if (N_ITER == iter_update){
        /* Alpha Sweep Driver. */
        if (strcmp(driver_coef, "CLS") == 0){
            Coef2 = CLS;
            Delta_angle_rad = Delta_Alpha_rad;
            Delta_angle_rad_slope = Delta_Alpha_rad_slope;
            Delta_Coef_tol = Delta_CL_tol;
        }
        /* Beta Sweep Driver. */
        if (strcmp(driver_coef, "CYS") == 0){
            Coef2 = CYS;
            Delta_angle_rad = Delta_Beta_rad;
            Delta_angle_rad_slope = Delta_Beta_rad_slope;
            Delta_Coef_tol = Delta_CY_tol;
        }

        Delta_Coef = Coef2 - Coef1;

        if (N_ITER == iter_slope){
            slope = Delta_Coef/Delta_angle_rad_slope;
            if (strcmp(driver_coef, "CLS") == 0){
                Message0("\n  CLa EVALUATION CONCLUDED %9.6f\n\n", slope);
            }
            else{
                Message0("\n  CYb EVALUATION CONCLUDED %9.6f\n\n", slope);
            }

        }

        Delta_Coef_target = Coef_target - Coef2;

        if (fabs(Delta_Coef_target) > Delta_Coef_tol){
            Delta_angle_rad = Delta_Coef_target/slope;
            Delta_angle_deg = Delta_angle_rad/M_PI * 180.0;
        
            if (fabs(Delta_angle_deg) > Delta_angle_deg_max){
                if (Delta_angle_deg > 0.0){
                    Delta_angle_rad_max = Delta_angle_deg_max * M_PI / 180.0;
                    Delta_angle_rad = Delta_angle_rad_max;
                }
                else{
                    Delta_angle_rad_max = -1.0*Delta_angle_deg_max * M_PI / 180.0;
                    Delta_angle_rad = Delta_angle_rad_max;
                }
            }

            angle_rad = angle_rad + Delta_angle_rad;

            /* Alpha Sweep Driver. */
            if (strcmp(driver_coef, "CLS") == 0){
                Alpha_rad = angle_rad;
                Alpha_deg = Alpha_rad/M_PI * 180.0;
                Delta_Alpha_rad = Delta_angle_rad;
                Delta_Alpha_deg = Delta_Alpha_rad/M_PI * 180.0;
                Message0("  %9s %9s\n", "CLCURR", "ALPHA");
                Message0("  %9.6f %9.6f\n\n", Coef2, Alpha_deg);

            }
            /* Beta Sweep Driver. */
            if (strcmp(driver_coef, "CYS") == 0){
                Beta_rad = angle_rad;
                Beta_deg = Beta_rad/M_PI * 180.0;
                Delta_Beta_rad = Delta_angle_rad;
                Delta_Beta_deg = Delta_Beta_rad/M_PI * 180.0;
                Message0("  %9s %9s\n", "CYCURR", "BETA");
                Message0("  %9.6f %9.6f\n\n", Coef2, Beta_deg);
            }

            x_flow_direction =  cos(Alpha_rad)*cos(Beta_rad);
            y_flow_direction = -cos(Alpha_rad)*sin(Beta_rad);
            z_flow_direction =  sin(Alpha_rad);
        }

        Coef1 = Coef2;
        iter_update = iter_update + delta_iter_update;
    }

    /*Memory is freed.*/
    free(cl_z_axis_cfd_model_body);
    free(cd_x_axis_cfd_model_body);
    free(cy_y_axis_cfd_model_body);
    free(cr_x_axis_cfd_model_body);
    free(cm_y_axis_cfd_model_body);
    free(cn_z_axis_cfd_model_body);
    free(ids_cl);
    free(ids_cd);
    free(ids_cy);
    free(ids_cr);
    free(ids_cm);
    free(ids_cn);
}
/* Update the boundary conditions for the flow direction components. */
DEFINE_PROFILE(x_component_flow_direction,t,i){
    face_t f;
    begin_f_loop(f,t){
        F_PROFILE(f,t,i) = x_flow_direction;
    }
    end_f_loop(f,t)
}
DEFINE_PROFILE(y_component_flow_direction,t,i){
	face_t f;
	begin_f_loop(f,t){
		F_PROFILE(f,t,i) = y_flow_direction;
	}
	end_f_loop(f,t)
}
DEFINE_PROFILE(z_component_flow_direction,t,i){
	face_t f;
	begin_f_loop(f,t){
	    F_PROFILE(f,t,i) = z_flow_direction;
	}
	end_f_loop(f,t)
}
