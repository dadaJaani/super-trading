import {
  Column,
  CreateDateColumn,
  Entity,
  OneToMany,
  PrimaryColumn,
} from 'typeorm';
import { Signal } from './signal.entity';
import { Trade } from './trade.entity';

@Entity('bots')
export class Bot {
  @PrimaryColumn('text')
  id: string;

  @Column('text', { nullable: true })
  name: string | null;

  @Column('text', { nullable: true })
  instrument: string | null;

  @Column('text', { nullable: true })
  strategy: string | null;

  @Column('text', { nullable: true })
  status: string | null;

  @Column('jsonb', { nullable: true })
  config: Record<string, unknown> | null;

  @CreateDateColumn({ type: 'timestamptz', name: 'created_at' })
  createdAt: Date;

  @OneToMany(() => Trade, (trade) => trade.bot)
  trades: Trade[];

  @OneToMany(() => Signal, (signal) => signal.bot)
  signals: Signal[];
}
