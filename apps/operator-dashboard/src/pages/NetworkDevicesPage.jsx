import { useEffect, useRef, useState } from 'react'
import { demoDataEnabled } from '../../../shared/demoMode.js'
import { getStaffNetworkInventory, runPingSweep, StaffSessionError, syncGatewayState } from '../api.js'
import '../styles/network-devices.css'

const dateTime = new Intl.DateTimeFormat('en-KE', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'Africa/Nairobi',
})
const deviceStatusLabels = { online: 'Online', offline: 'Offline', degraded: 'Degraded' }

function toDevices({ routers, access_points: accessPoints }) {
  const routerNames = new Map(routers.map((router) => [router.id, router.name]))
  return [
    ...routers.map((router) => ({
      key: `router-${router.id}`,
      id: router.name,
      type: 'Core gateway',
      identity: router.identity,
      heartbeat: router.last_synced_at ? dateTime.format(new Date(router.last_synced_at)) : null,
      hotspot: router.hotspot_enabled == null ? null : router.hotspot_enabled ? "Enabled" : "Disabled",
      status: deviceStatusLabels[router.status.toLowerCase()] ?? 'Unknown',
    })),
    ...accessPoints.map((point) => ({
      key: `access-point-${point.id}`,
      id: point.name,
      type: 'Access point',
      site: point.location,
      mac: point.mac_address,
      routerName: routerNames.get(point.router_id),
      status: deviceStatusLabels[point.status.toLowerCase()] ?? 'Unknown',
      heartbeat: point.last_seen_at ? dateTime.format(new Date(point.last_seen_at)) : null,
    })),
  ]
}

const sampleDevices = [
  { id: 'KE-NBO-CORE-01', type: 'Core gateway', site: 'Westlands Core Hub', address: '192.0.2.11', status: 'Online', heartbeat: '08:42 EAT', sessions: 24 },
  { id: 'KE-KLI-CORE-01', type: 'Core gateway', site: 'Kilimani PoP', address: '192.0.2.12', status: 'Online', heartbeat: '08:42 EAT', sessions: 18 },
  { id: 'AP-Westlands-02', type: 'Access point', site: 'Nairobi HQ · Westlands Sector 2', address: '192.0.2.22', status: 'Online', heartbeat: '12s before snapshot', sessions: 3, model: 'Ubiquiti UniFi 6 Pro', mac: '02:00:00:00:00:22', firmware: 'v6.5.62' },
  { id: 'AP-Westlands-04', type: 'Access point', site: 'Westlands Zone 04', address: '192.0.2.24', status: 'Degraded', heartbeat: '08:39 EAT', sessions: 8 },
  { id: 'AP-Westlands-01', type: 'Access point', site: 'Westlands Zone 01', address: '192.0.2.21', status: 'Online', heartbeat: '08:41 EAT', sessions: 14 },
  { id: 'AP-Kilimani-02', type: 'Access point', site: 'Kilimani Zone 02', address: '192.0.2.32', status: 'Online', heartbeat: '08:41 EAT', sessions: 12 },
  { id: 'AP-CBD-BusStation-01', type: 'Access point', site: 'CBD Transit Hub', address: '192.0.2.41', status: 'Offline', heartbeat: '07:58 EAT', sessions: 0 },
]

const featuredSubscribers = [
  { name: 'Amina Wanjiku', initials: 'AW', package: 'Weekly Plus', usage: '3.42 GB used' },
  { name: 'John Kariuki', initials: 'JK', package: 'Daily Unlimited', usage: '1.2 GB used' },
  { name: 'Esther Kemboi', initials: 'EK', package: 'Weekly Plus', usage: '580 MB used' },
]

const featuredEvents = [
  ['08:30 EAT', 'New subscriber lease assigned', 'Sample DHCP pool: Westlands A'],
  ['04:12 EAT', 'Channel optimization scan completed', 'No interference in this sample'],
  ['23:00 EAT, previous day', 'Routine telemetry ping', 'Sample latency: 4 ms'],
]

const deviceTypes = ['All Devices', 'Core gateway', 'Access point']

function DeviceStatus({ status }) {
  return <span className="network-device-status" data-status={status}>{status}</span>
}

function DeviceDetails({ device, opener, onClose, live }) {
  const dialogRef = useRef(null)
  const featured = !live && device.id === 'AP-Westlands-02'

  useEffect(() => {
    const dialog = dialogRef.current
    dialog.showModal()
    return () => {
      dialog.close()
      if (opener.isConnected) opener.focus()
    }
  }, [opener])

  return (
    <dialog ref={dialogRef} className="network-device-drawer" aria-labelledby="network-device-title" onCancel={(event) => {
      event.preventDefault()
      onClose()
    }}>
      <div className="network-drawer-layout">
        <header>
          <div>
            <p className="network-device-eyebrow">{live ? 'Saved device details' : 'Device details · Demo'}</p>
            <h2 id="network-device-title">{device.id}</h2>
            <p>{device.type}{device.model ? ` · ${device.model}` : ''}</p>
          </div>
          <button type="button" aria-label="Close device details" onClick={onClose}>×</button>
        </header>

        <div className="network-drawer-body">
          <section className="network-device-card network-identity-card">
            <div className="network-card-heading">
              <DeviceStatus status={device.status} />
              <small>{device.firmware ? `Firmware: ${device.firmware}` : 'Firmware unavailable'}</small>
            </div>
            <dl className="network-identity-fields">
              {live ? (
                <div><dt>{device.type === 'Core gateway' ? 'Router identity' : 'Registered router'}</dt><dd>{device.identity || device.routerName || 'Unavailable'}</dd></div>
              ) : (
                <div><dt>IP Address</dt><dd>{device.address}</dd></div>
              )}
              <div><dt>MAC Address</dt><dd>{device.mac ?? 'Unavailable'}</dd></div>
            </dl>
            <p className="network-device-location">{device.site || 'Location unavailable'}</p>
          </section>

          <section>
            <div className="network-card-heading"><h3>Vital Telemetry</h3><small>{live ? 'Recorded data' : 'Fixed sample'}</small></div>
            <dl className="network-telemetry-grid">
              <div><dt>{live ? 'Last recorded sighting (EAT)' : 'Last Heartbeat'}</dt><dd>{device.heartbeat || 'Unavailable'}</dd></div>
              <div><dt>System Uptime</dt><dd>{featured ? '42d 18h' : 'Unavailable'}</dd></div>
              <div><dt>RF Channels</dt><dd>{featured ? '5 GHz Ch 36 · 2.4 GHz Ch 6' : 'Unavailable'}</dd></div>
              <div><dt>Hardware Load</dt><dd>{featured ? 'CPU 28% · RAM 44%' : 'Unavailable'}</dd></div>
            </dl>
          </section>

          <section>
            <div className="network-card-heading"><h3>Associated Active Subscribers</h3>{!live && <small>{device.sessions} sample sessions</small>}</div>
            {featured ? (
              <ul className="network-related-list">
                {featuredSubscribers.map((subscriber) => (
                  <li key={subscriber.name}>
                    <span className="network-subscriber-avatar" aria-hidden="true">{subscriber.initials}</span>
                    <strong>{subscriber.name}</strong>
                    <div><span>{subscriber.package}</span><small>{subscriber.usage}</small></div>
                  </li>
                ))}
              </ul>
            ) : <p>Individual subscriber details are unavailable for this device.</p>}
          </section>

          <section>
            <div className="network-card-heading"><h3>Recent Diagnostic Events</h3>{!live && <small>Sample log</small>}</div>
            {featured ? (
              <ol className="network-event-list">
                {featuredEvents.map(([time, title, detail]) => (
                  <li key={title}><strong>{title}</strong><small>{time} · {detail}</small></li>
                ))}
              </ol>
            ) : <p>{live ? 'Diagnostic history is unavailable.' : 'No diagnostic events in this sample record.'}</p>}
          </section>
        </div>

        <footer>
          <p>{live ? 'Device diagnostics are unavailable.' : 'Diagnostics are unavailable in demo mode.'}</p>
          <div className="network-device-actions">
            {!live && <button type="button" disabled>Run Ping Test</button>}
            <button type="button" className="network-device-primary" onClick={onClose}>Close Drawer</button>
          </div>
        </footer>
      </div>
    </dialog>
  )
}

export default function NetworkDevicesPage({ accessToken, onSignOut, isAdmin = false } = {}) {
  return accessToken || demoDataEnabled ? <NetworkInventory accessToken={accessToken} onSignOut={onSignOut} isAdmin={isAdmin} /> : (
    <section className="network-devices-page">
      <h1>Network &amp; Devices</h1>
      <p role="status">Network inventory is currently unavailable.</p>
    </section>
  )
}

function NetworkInventory({ accessToken, onSignOut, isAdmin }) {
  const live = Boolean(accessToken)
  const [inventory, setInventory] = useState({ records: [], loading: live })
  const [reload, setReload] = useState(0)
  const [running, setRunning] = useState('')
  const [checkError, setCheckError] = useState('')
  const [sweep, setSweep] = useState(null)
  const [gateway, setGateway] = useState(null)

  async function runCheck(action) {
    if (running) return
    setRunning(action)
    setCheckError('')
    try {
      if (action === 'sweep') setSweep(await runPingSweep(accessToken))
      else {
        const result = await syncGatewayState(accessToken)
        setGateway(result)
        if (!result.simulated) setReload((attempt) => attempt + 1)
      }
    } catch (failure) {
      if (failure instanceof StaffSessionError) onSignOut?.()
      else setCheckError(failure.message)
    } finally {
      setRunning('')
    }
  }

  useEffect(() => {
    if (!accessToken) return undefined
    const controller = new AbortController()
    const { signal } = controller
    getStaffNetworkInventory(accessToken, { signal }).then((record) => {
      if (!signal.aborted) setInventory({ records: toDevices(record) })
    }).catch((error) => {
      if (signal.aborted) return
      if (error instanceof StaffSessionError) onSignOut?.()
      else setInventory({ records: [], error: 'Could not load device inventory. Please try again.' })
    })
    return () => controller.abort()
  }, [accessToken, onSignOut, reload])

  function refresh() {
    setInspection(null)
    setInventory({ records: [], loading: true })
    setSector('')
    setReload((attempt) => attempt + 1)
  }

  const [search, setSearch] = useState('')
  const [type, setType] = useState('All Devices')
  const [status, setStatus] = useState('')
  const [sector, setSector] = useState('')
  const [attentionFirst, setAttentionFirst] = useState(false)
  const [inspection, setInspection] = useState(null)

  const term = search.trim().toLowerCase()
  const devices = live ? inventory.records : sampleDevices
  const sectors = live ? [...new Set(devices.map((device) => device.site).filter(Boolean))] : ['Westlands', 'Kilimani', 'CBD']
  const statusOrder = { Offline: 0, Degraded: 1, Online: 2 }
  const visible = devices.filter((device) =>
    (type === 'All Devices' || device.type === type)
    && (!status || device.status === status)
    && (!sector || (live ? device.site === sector : `${device.id} ${device.site}`.toLowerCase().includes(sector.toLowerCase())))
    && [device.id, device.address, device.site, device.mac, device.identity, device.routerName].some((value) => (value ?? '').toLowerCase().includes(term)),
  )
  if (attentionFirst) visible.sort((first, second) => (statusOrder[first.status] ?? 3) - (statusOrder[second.status] ?? 3))

  const gateways = devices.filter((device) => device.type === 'Core gateway')
  const known = !inventory.loading && !inventory.error
  const metrics = live ? [
    ['Registered Routers', known ? gateways.length : 'Unavailable', 'Saved router inventory'],
    ['Access Points Recorded Online', known ? devices.filter((device) => device.type === 'Access point' && device.status === 'Online').length : 'Unavailable', 'Last saved status'],
    ['Devices Recorded Offline', known ? devices.filter((device) => device.status === 'Offline').length : 'Unavailable', 'Last saved status'],
    ['Network Integration Status', 'Inventory', 'Run an administrator check for a current reading'],
  ] : [
    ['Connected Routers', `${gateways.filter((device) => device.status === 'Online').length}/${gateways.length}`, 'Core gateways online'],
    ['Online Access Points', sampleDevices.filter((device) => device.type === 'Access point' && device.status === 'Online').length, 'Access points online'],
    ['Offline Devices', sampleDevices.filter((device) => device.status === 'Offline').length, 'Devices awaiting review'],
    ['Network Integration Status', 'Demo', 'Fixed inventory snapshot'],
  ]

  return (
    <section className="network-devices-page">
      <div className="page-heading network-devices-heading">
        <div>
          <p className="network-device-eyebrow">{live ? 'Infrastructure inventory' : 'Infrastructure Telemetry · Cluster KE-NBO-01'}</p>
          <h1>Network &amp; Devices</h1>
          <p>{live ? 'Review registered routers, access points and their last recorded statuses.' : 'Review gateway and access point status across the network.'}</p>
        </div>
        <div className="network-device-actions">
          {live ? (
            <button type="button" className="network-device-primary" disabled={inventory.loading} onClick={refresh}>Refresh</button>
          ) : <span className="network-fixed-label">Fixed snapshot</span>}
          {live && isAdmin && <>
            <button type="button" className="network-ping-sweep" disabled={Boolean(running)} onClick={() => runCheck('sweep')}>
              {running === 'sweep' ? 'Checking devices…' : 'Run Ping Sweep'}
            </button>
            <button type="button" disabled={Boolean(running)} onClick={() => runCheck('sync')}>
              {running === 'sync' ? 'Syncing…' : 'Sync Gateway State'}
            </button>
          </>}
          {!live && <>
            <button type="button" className="network-ping-sweep" disabled>Run Ping Sweep</button>
            <button type="button" disabled>Sync Gateway State</button>
          </>}
        </div>
      </div>
      {!live && <p className="network-device-demo"><strong>Demo data.</strong> This inventory is a fixed sample. Live sync and diagnostics are unavailable.</p>}

      {checkError && <p role="alert">{checkError}</p>}
      {gateway && <p role="status">
        {gateway.simulated ? 'Simulated gateway reading' : 'Gateway synced'} · {gateway.identity} · Hotspot {gateway.hotspot_enabled ? 'enabled' : 'disabled'} · {dateTime.format(new Date(gateway.checked_at))}
      </p>}
      {sweep && <section className="network-device-card" aria-label="Ping sweep results" aria-live="polite">
        <h2>{sweep.simulated ? 'Simulated ping sweep' : 'Ping sweep results'}</h2>
        <p>{dateTime.format(new Date(sweep.checked_at))} · A device may be online without answering a ping.</p>
        {sweep.results.length ? <ul>
          {sweep.results.map(({ key, name, result }) => <li key={key}>{name} · {({
            reachable: 'Reachable', no_response: 'No response', no_address: 'No address',
            unsupported_address: 'No supported management address', unavailable: 'Check unavailable',
          })[result]}</li>)}
        </ul> : <p>No devices are registered.</p>}
        {sweep.truncated && <p>Showing the first 20 routers and 20 access points.</p>}
      </section>}

      <section className="network-device-metrics" aria-label="Inventory totals">
        {metrics.map(([label, value, description]) => (
          <article className="network-device-card" key={label}>
            <h2>{label}</h2><strong>{value}</strong><p>{description}</p>
          </article>
        ))}
      </section>

      <section className="network-device-card network-device-filters" aria-label="Filter equipment inventory">
        <input type="search" aria-label="Search network devices" placeholder={live ? 'Search name, identity, MAC or location' : 'Search device, IP, MAC, or location'} value={search} onChange={(event) => setSearch(event.target.value)} />
        <select aria-label="Filter by device type" value={type} onChange={(event) => setType(event.target.value)}>
          {deviceTypes.map((item) => <option key={item}>{item}</option>)}
        </select>
        <select aria-label={live ? 'Filter by location' : 'Filter by sector'} value={sector} onChange={(event) => setSector(event.target.value)}>
          <option value="">{live ? 'All Locations' : 'All Sectors'}</option>
          {sectors.map((item) => <option key={item}>{item}</option>)}
        </select>
        <select aria-label={live ? 'Filter by recorded status' : 'Filter by connection status'} value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">All States</option>
          {(live ? ['Online', 'Degraded', 'Offline', 'Unknown'] : ['Online', 'Degraded', 'Offline']).map((item) => <option key={item}>{item}</option>)}
        </select>
        <button type="button" aria-pressed={attentionFirst} onClick={() => setAttentionFirst(!attentionFirst)}>Needs Attention First</button>
      </section>

      <section className="network-device-inventory" aria-labelledby="equipment-inventory-title">
        <div className="network-device-inventory-heading"><h2 id="equipment-inventory-title">Equipment Inventory</h2><p>{live ? known && `${devices.length} registered devices` : `${sampleDevices.length} sample devices`}</p></div>
        <div className="network-device-table-scroll" role="region" aria-label="Scrollable device inventory" tabIndex={0}>
          <table>
            <thead><tr>{['Device Identifier', 'Device Type', 'Deployment Location', live ? 'Recorded Status' : 'Connection State', live ? 'Last Seen (EAT)' : 'Last Seen', 'Actions'].map((column) => <th scope="col" key={column}>{column}</th>)}</tr></thead>
            <tbody>
              {visible.map((device) => (
                <tr key={device.key ?? device.id}>
                  <th scope="row">{device.id}<small>{live ? device.identity || device.mac : device.address}</small></th>
                  <td>{device.type}</td><td>{device.site || 'Unavailable'}</td><td><DeviceStatus status={device.status} /></td><td>{device.heartbeat || 'Unavailable'}{device.hotspot && <small> · Hotspot {device.hotspot.toLowerCase()}</small>}</td>
                  <td><button type="button" aria-label={`View device ${device.id}`} onClick={(event) => setInspection({ device, opener: event.currentTarget })}>View Drawer</button></td>
                </tr>
              ))}
              {visible.length === 0 && <tr><td colSpan={6}>
                {live ? inventory.error ? <span role="alert">{inventory.error}</span>
                  : <span role="status">{inventory.loading ? 'Loading device inventory…' : devices.length ? 'No devices match your filters.' : 'No network devices are registered.'}</span>
                  : 'No sample devices match your filters.'}
              </td></tr>}
            </tbody>
          </table>
        </div>
        <p className="network-device-results" aria-live="polite">{live ? known && `Showing ${visible.length} of ${devices.length} registered devices` : `Showing ${visible.length} of ${sampleDevices.length} sample devices`}</p>
      </section>

      <aside className="network-device-card network-integration-note">
        <strong>{live ? 'Device inventory' : 'Cluster Telemetry'}</strong>
        <p>{live ? 'Statuses are saved inventory values. Refresh reloads the saved records.' : 'Fixed dashboard snapshot. Live gateway sync and audit export are unavailable.'}</p>
      </aside>

      {inspection && <DeviceDetails live={live} device={inspection.device} opener={inspection.opener} onClose={() => setInspection(null)} />}
    </section>
  )
}
