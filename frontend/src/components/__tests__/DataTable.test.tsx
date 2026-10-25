import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { DataTable, Pagination, type Column } from '../DataTable'

interface Row {
  id: number
  name: string
  city: string
}
const columns: Column<Row>[] = [
  { key: 'name', header: 'Name', sortKey: 'name', render: (r) => r.name },
  { key: 'city', header: 'City', render: (r) => r.city },
]
const rows: Row[] = [
  { id: 1, name: 'Ana', city: 'Porto' },
  { id: 2, name: 'Rui', city: 'Braga' },
]

describe('DataTable', () => {
  it('exposes sort state and sorts on click', async () => {
    const onSort = vi.fn()
    render(
      <DataTable caption="People" columns={columns} rows={rows} rowKey={(r) => r.id} sort="name" order="desc" onSort={onSort} mobileTitle={(r) => r.name} />,
    )
    const table = screen.getByRole('table')
    const header = within(table).getByRole('columnheader', { name: /name/i })
    expect(header).toHaveAttribute('aria-sort', 'descending')
    expect(within(table).getByRole('columnheader', { name: 'City' })).not.toHaveAttribute('aria-sort')
    await userEvent.click(within(header).getByRole('button'))
    expect(onSort).toHaveBeenCalledWith('name')
  })

  it('renders a card list for small screens', () => {
    render(<DataTable caption="People" columns={columns} rows={rows} rowKey={(r) => r.id} mobileTitle={(r) => `Card ${r.name}`} />)
    const list = screen.getByRole('list', { name: 'People' })
    expect(within(list).getAllByRole('listitem')).toHaveLength(2)
    expect(within(list).getByText('Card Ana')).toBeInTheDocument()
  })
})

describe('Pagination', () => {
  it('shows the range and disables buttons at the ends', async () => {
    const onPage = vi.fn()
    render(<Pagination page={1} pageSize={20} total={45} onPage={onPage} />)
    expect(screen.getByText('1–20 of 45')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(onPage).toHaveBeenCalledWith(2)
  })

  it('handles an empty result', () => {
    render(<Pagination page={1} pageSize={20} total={0} onPage={() => {}} />)
    expect(screen.getByText('0–0 of 0')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  })
})
