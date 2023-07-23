import { useContext } from "react";
import {  AppContext } from "../../../../context/appMainContext"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTableColumns, faCheck } from "@fortawesome/free-solid-svg-icons";
import { panelStateInterface } from "../../../../interface/appMainContext_interface";

import css from "./header_fn_btn_view.module.css"


export default function HeaderFNBtnView(){
  let context = useContext(AppContext);

  //handle panel show hide
  function panelShowHandler(selectedPanelName:string){
    context.setPanelState((prev:any) => {
      return prev.map((el : { panelName:string, show:boolean }) => {
        if(el.panelName === selectedPanelName){
          return {...el, show : !el.show}
        }else{
          return el;
        }
      });
    })
  }
  
  //map view list base on state
  let viewList = context.panelState.map((el:panelStateInterface, index:number) =>{
    return(
      <li key={el.panelName + index} className={`mb-sm ${css.header_fn_btn_each_view}`} onClick={() => panelShowHandler(el.panelName)}>
        <span>{el.panelName}</span>
        {el.show ? <FontAwesomeIcon icon={faCheck} /> : ""}
      </li>
    )
  });

  return(
    <>
      <li className={`${css.header_fn_btn_wrapper_li} header_each_btn` }>
        <FontAwesomeIcon icon={faTableColumns} className="mr-sm" />
        View
        <ul className={`crd_shadow-light ${css.header_fn_btn_hover_ul}`}>
          {viewList}
        </ul>
      </li>
    </>
  )
}