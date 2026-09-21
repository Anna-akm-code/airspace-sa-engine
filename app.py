"""Read-only visual presentation; live API execution stays in detect_only.py."""

import json
from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components

from sa_engine.demo import demo_report
from sa_engine.map_view import render_map
from sa_engine.report import LIMITATIONS, alert_text, latest_live_report, report_text


def main():
    st.set_page_config(page_title='Airspace SA Engine', layout='wide')
    st.title('Airspace SA Engine')
    st.caption('A small common operating picture of loaded data, observations and modeled alerts.')
    mode = st.sidebar.radio('Data mode', ['Synthetic Demo', 'Latest saved live run'])
    st.warning(LIMITATIONS)
    try:
        if mode == 'Synthetic Demo':
            report = demo_report()
        else:
            root = st.sidebar.text_input('Artifact directory', 'runs')
            report = latest_live_report(root)
            if report is None:
                st.info('No saved live artifact bundle. Run python detect_only.py first. Old JSONL alone does not contain the full map/alert snapshot.')
                return
        st.subheader(report['label'])
        run = report['run']
        timestamp = datetime.fromtimestamp(run['run_timestamp'],timezone.utc).isoformat()
        st.caption(f"Run {run['run_id']} | {timestamp} | Freshness is measured at that run, not now.")
        if report['mode'] == 'synthetic':
            st.info('All demo aircraft, infrastructure, timestamps and track observations are invented. No real incident is depicted.')
        else:
            st.info('Saved snapshot, not a continuously updating surveillance feed.')
        columns = st.columns(5)
        for column, label, value in zip(columns,['Zones','Aircraft','Fresh','Stale','Alerts'],
            [len(report['zones']),len(report['aircraft']),run['fresh_count'],run['stale_count'],len(report['alerts'])]):
            column.metric(label,value)
        components.html(render_map(report).get_root().render(),height=620,scrolling=True)
        st.subheader('Alerts')
        if not report['alerts']:
            st.info('No modeled alerts in this run. Zero alerts is a valid result, not a safety determination.')
        for alert in report['alerts']:
            with st.expander(f"{alert['aircraft']['callsign'] or alert['aircraft']['icao24']} - {alert['zone']['name']} - {alert['verification_status'].upper()}",expanded=True):
                st.text(alert_text(alert))
                if alert['recent_positions']:
                    st.dataframe(alert['recent_positions'],hide_index=True)
        st.download_button('Download JSON report',json.dumps(report,indent=2,allow_nan=False),
                           file_name='alerts.json',mime='application/json')
        st.download_button('Download text report',report_text(report),file_name='alerts.txt')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        st.error(f'Unable to display report: {type(exc).__name__}. Check the local artifact schema and files.')


if __name__ == '__main__':
    main()
