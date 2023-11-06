import { useContext, useEffect } from "react";
import {AppContext} from "../../context/appMainContext";

import { PanelGroup, Panel, PanelResizeHandle} from "react-resizable-panels";
import FlowsheetHeader from "./flowsheet_component/flowsheet_header/flowsheet_header_component";
import MinimizedBar from "./minimized_bar_component/minimized_bar_component";
import Flowsheet from "./flowsheet_component/flowsheet_component";
import FlowsheetDiagnostics from "./flowsheet_diagnostics_component/flowsheet_diagnostics_component";
import StreamTable from "./stream_table_component/stream_table";

import { MainFV } from "./flowsheet_component/flowsheet_functions/mainFV";

import css from "./flowsheet_wrapper.module.css";

export default function FlowsheetWrapper(){

	let {server_port, fv_id, panelState} = useContext(AppContext);
	const isFvShow:boolean = panelState.fv.show;
	const isDiagnosticsShow:boolean = panelState.diagnostics.show;
	const isStreamTableShow = panelState.streamTable.show;

	const panelShow = {display:"block"};
	const panelHide = {display:"none"};

  useEffect(()=>{
    //get server port base on UI port number, vite running on 5173 on dev
    server_port == "5173" ? server_port = 8000 : server_port = server_port;
    //when template loaded then render flowsheet, variable, stream table to page with minFV class.
    const fv = new MainFV(fv_id, server_port, isFvShow, false, isStreamTableShow); //The false is placeholder for isVariableShow, now variable panel is not show
    
    return ()=>{
        fv.cleanToolBarEvent()
    }
  },[isFvShow, isStreamTableShow])

	return(
		<div id="flowsheet-wrapper" className={css.flowsheetWrapper}>
			<MinimizedBar />
			<PanelGroup direction="horizontal">
				<Panel defaultSize={65}>
					<PanelGroup direction="vertical">
						{
							isFvShow && 
							<Panel defaultSize={isFvShow ? 65 : 0} maxSize={100} >
								<FlowsheetHeader />
								<Flowsheet />
							</Panel>
						}
						<PanelResizeHandle className="panelResizeHandle panelResizeHandle_horizontal"/>
						{
							isStreamTableShow &&
							<Panel maxSize={100} defaultSize={35} style={isStreamTableShow ? panelShow : panelHide}>
								<StreamTable />
							</Panel>
						}
					</PanelGroup>
				</Panel>
				<PanelResizeHandle className="panelResizeHandle panelResizeHandle_vertical"/>
					{
						isDiagnosticsShow && 
						<Panel defaultSize={isFvShow ? 35 : 100} minSize={0}>
						<FlowsheetDiagnostics />
						</Panel>
					}
			</PanelGroup>
		</div>
	)
}