const payments = [
  {
    reference: 'RJ92MN41P0',
    customer: 'Amina Wanjiku',
    phone: '+254 712 345 678',
    package: 'Weekly Plus 10GB',
    amount: 'KES 250',
    paymentStatus: 'Confirmed',
    activationStatus: 'Active',
    time: '14:45 EAT',
  },
  {
    reference: 'RJ92MN38X2',
    customer: 'Dennis Kiprono',
    phone: '+254 722 890 123',
    package: 'Daily Unlimited',
    amount: 'KES 100',
    paymentStatus: 'Confirmed',
    activationStatus: 'Activation Failed',
    time: '14:41 EAT',
  },
  {
    reference: 'STK_PEND_884',
    customer: 'Faith Muthoni',
    phone: '+254 705 441 902',
    package: '3-Hour Study',
    amount: 'KES 35',
    paymentStatus: 'Pending',
    activationStatus: 'Activation Pending',
    time: '14:39 EAT',
  },
  {
    reference: 'RJ92MN11K9',
    customer: 'Kevin Ombati',
    phone: '+254 791 204 558',
    package: 'Monthly Kiosk',
    amount: 'KES 1,200',
    paymentStatus: 'Confirmed',
    activationStatus: 'Active',
    time: '14:32 EAT',
  },
  {
    reference: 'RJ92MN09H4',
    customer: 'Lilian Cherotich',
    phone: '+254 748 119 023',
    package: 'Daily Connect',
    amount: 'KES 50',
    paymentStatus: 'Confirmed',
    activationStatus: 'Active',
    time: '14:18 EAT',
  },
]

function StatusBadge({ status, type }) {
  const statusClass = status.toLowerCase().replaceAll(' ', '-')

  return (
    <span className={`payment-status ${type}-${statusClass}`}>
      {status}
    </span>
  )
}

export default function RecentPayments() {
  return (
    <section className="payments-section">
      <div className="payments-heading">
        <div>
          <p className="section-eyebrow">TRANSACTION ACTIVITY</p>
          <h2>Recent Payments</h2>
          <p className="section-description">
            Latest sample subscriber transactions
          </p>
        </div>

        <span className="demo-data-label">DEMO DATA</span>
      </div>

      <div className="payments-table-wrapper">
        <table className="payments-table">
          <thead>
            <tr>
              <th scope="col">TRANSACTION / CUSTOMER</th>
              <th scope="col">PACKAGE</th>
              <th scope="col">AMOUNT</th>
              <th scope="col">PAYMENT</th>
              <th scope="col">ACTIVATION</th>
              <th scope="col">TIME</th>
            </tr>
          </thead>

          <tbody>
            {payments.map((payment) => (
              <tr key={payment.reference}>
                <td>
                  <div className="payment-customer">
                    <strong>{payment.customer}</strong>
                    <span>{payment.phone}</span>
                    <small>{payment.reference}</small>
                  </div>
                </td>

                <td>{payment.package}</td>
                <td className="payment-amount">{payment.amount}</td>

                <td>
                  <StatusBadge
                    status={payment.paymentStatus}
                    type="payment"
                  />
                </td>

                <td>
                  <StatusBadge
                    status={payment.activationStatus}
                    type="activation"
                  />
                </td>

                <td className="payment-time">{payment.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="payments-footnote">
        Illustrative transactions only. No live payment records are connected.
      </p>
    </section>
  )
}
