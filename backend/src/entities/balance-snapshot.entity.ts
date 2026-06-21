import { Column, Entity, PrimaryColumn } from 'typeorm';

@Entity('balance_snapshots')
export class BalanceSnapshot {
  @PrimaryColumn('timestamptz')
  time: Date;

  @PrimaryColumn('text', { name: 'account_ref' })
  accountRef: string;

  @Column('decimal')
  balance: string;

  @Column('decimal', { nullable: true })
  nav: string | null;

  @Column('text', { nullable: true, default: 'oanda' })
  source: string | null;
}
